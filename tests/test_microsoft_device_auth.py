"""MINEVORA Microsoft/Xbox/Minecraft authentication tests using mock responses only."""
import importlib.util
import io
import json
import os
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("minevora_auth",ROOT/"tools"/"microsoft_minecraft_device_auth.py")
auth=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=auth
spec.loader.exec_module(auth)

TEST_CLIENT="a1b2c3d4-1111-2222-3333-444455556666"


class FakeResponse(io.BytesIO):
    def __init__(self, payload):
        super().__init__(json.dumps(payload).encode("utf-8"))


class EndpointSimulator:
    def __init__(self):
        self.urls=[]
        self.claim={"DisplayClaims":{"xui":[{"uhs":"UHS_TEST"}]},"Token":"XBOX_TOKEN"}
        self.xsts={"DisplayClaims":{"xui":[{"uhs":"UHS_TEST"}]},"Token":"XSTS_TOKEN"}
        self.game_token={"access_token":"MINECRAFT_TOKEN"}
        self.entitlements={"items":[{"name":"game_minecraft"}]}
        self.profile={"id":"d42cf61a3d8c45c1b7b427b69d3acf19","name":"MinecraftUser"}
    def __call__(self,request,timeout=None):
        self.urls.append((request.full_url,request.get_method(),request.headers))
        payloads={auth.XBOX_USER_ENDPOINT:self.claim,auth.XSTS_ENDPOINT:self.xsts,
                  auth.MINECRAFT_LOGIN_ENDPOINT:self.game_token,
                  auth.MINECRAFT_ENTITLEMENTS:self.entitlements,auth.MINECRAFT_PROFILE:self.profile}
        return FakeResponse(payloads[request.full_url])


class FakeMSAL:
    flow={"user_code":"ABCD-EFGH","verification_uri":"https://microsoft.com/devicelogin",
          "message":"Logowanie Microsoft"}
    token={"access_token":"FAKE_MS_ACCESS_TOKEN"}
    class PublicClientApplication:
        def __init__(self,client_id,authority):
            assert client_id==TEST_CLIENT
            assert authority==auth.AUTHORITY
        def initiate_device_flow(self,scopes):
            assert scopes==["XboxLive.signin"]
            return FakeMSAL.flow
        def acquire_token_by_device_flow(self,flow):
            assert flow is FakeMSAL.flow
            return FakeMSAL.token


class DeviceAuthTests(unittest.TestCase):
    def setUp(self):
        self.api=EndpointSimulator()
    def test_explicit_client_id(self):
        self.assertEqual(auth.public_client_id(TEST_CLIENT),TEST_CLIENT)
    def test_missing_or_invalid_client_id_is_rejected(self):
        for bad in ["","nonsense","https://localhost", "0000"]:
            with self.assertRaises(auth.AuthError):
                auth.public_client_id(bad or "not-a-guid")
    def test_successful_minecraft_ownership_validation(self):
        result=auth.exchange_for_minecraft("MS_TOKEN",opener=self.api)
        self.assertEqual(result.username,"MinecraftUser")
        self.assertEqual(len(self.api.urls),5)
        self.assertNotIn("MINECRAFT_TOKEN",repr(result))
        self.assertTrue(all(url.startswith("https://") for url,_,_ in self.api.urls))
    def test_no_entitlement_is_not_success(self):
        self.api.entitlements={"items":[]}
        with self.assertRaisesRegex(auth.AuthError,"uprawnień"):
            auth.exchange_for_minecraft("MS_TOKEN",opener=self.api)
    def test_xbox_user_hash_mismatch(self):
        self.api.xsts["DisplayClaims"]["xui"][0]["uhs"]="DIFFERENT"
        with self.assertRaisesRegex(auth.AuthError,"XSTS"):
            auth.exchange_for_minecraft("MS_TOKEN",opener=self.api)
    def test_no_java_profile_is_not_success(self):
        self.api.profile={"id":"not-uuid","name":"MinecraftUser"}
        with self.assertRaisesRegex(auth.AuthError,"identyfikatora"):
            auth.exchange_for_minecraft("MS_TOKEN",opener=self.api)
    def test_no_password_or_local_redirect(self):
        text=(ROOT/"tools"/"microsoft_minecraft_device_auth.py").read_text("utf-8")
        self.assertNotIn('localhost:',text)
        self.assertNotIn('client_secret',text)
        self.assertNotIn('input("Password',text)
    def test_device_code_callback_receives_only_code(self):
        captured=[]
        result=auth.authenticate_device_code(TEST_CLIENT,
             lambda url,code,msg: captured.append((url,code,msg)),
             msal_module=FakeMSAL,
             token_exchange=lambda token: "valid:"+token)
        self.assertEqual(result,"valid:FAKE_MS_ACCESS_TOKEN")
        self.assertEqual(captured,[("https://microsoft.com/devicelogin","ABCD-EFGH","Logowanie Microsoft")])
    def test_cancelled_login_is_not_success(self):
        original=FakeMSAL.token
        try:
            FakeMSAL.token={"error":"authorization_declined"}
            with self.assertRaisesRegex(auth.AuthError,"anulowane"):
                auth.authenticate_device_code(TEST_CLIENT,lambda *_:None,msal_module=FakeMSAL)
        finally:
            FakeMSAL.token=original
    def test_untrusted_device_code_url_rejected(self):
        original=FakeMSAL.flow
        try:
            FakeMSAL.flow={"user_code":"ABCD-EFGH","verification_uri":"https://not-microsoft.example/"}
            with self.assertRaisesRegex(auth.AuthError,"prawidłowego"):
                auth.authenticate_device_code(TEST_CLIENT,lambda *_:None,msal_module=FakeMSAL)
        finally:
            FakeMSAL.flow=original
    def test_missing_token_does_not_call_xbox(self):
        with self.assertRaisesRegex(auth.AuthError,"Brak tokenu"):
            auth.exchange_for_minecraft("",opener=self.api)
        self.assertFalse(self.api.urls)

if __name__=="__main__":
    unittest.main()
