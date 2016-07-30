import base64
import datetime
import json

import unittest
from mock import patch
from mock import MagicMock

import kmsauth
from kmsauth.utils import lru


class KMSTokenValidatorTest(unittest.TestCase):
    @patch(
        'kmsauth.services.get_boto_client',
        MagicMock()
    )
    def test_validate_config(self):
        with self.assertRaises(kmsauth.ConfigurationError):
            kmsauth.KMSTokenValidator(
                'alias/authnz-unittest',
                None,
                'kmsauth-unittest',
                'us-east-1',
                # 0 is an invalid token version
                minimum_token_version=0
            )
        with self.assertRaises(kmsauth.ConfigurationError):
            kmsauth.KMSTokenValidator(
                'alias/authnz-unittest',
                None,
                'kmsauth-unittest',
                'us-east-1',
                # 3 is an invalid token version
                minimum_token_version=3
            )
        with self.assertRaises(kmsauth.ConfigurationError):
            kmsauth.KMSTokenValidator(
                'alias/authnz-unittest',
                None,
                'kmsauth-unittest',
                'us-east-1',
                # 0 is an invalid token version
                maximum_token_version=0
            )
        with self.assertRaises(kmsauth.ConfigurationError):
            kmsauth.KMSTokenValidator(
                'alias/authnz-unittest',
                None,
                'kmsauth-unittest',
                'us-east-1',
                # 3 is an invalid token version
                maximum_token_version=3
            )
        with self.assertRaises(kmsauth.ConfigurationError):
            kmsauth.KMSTokenValidator(
                'alias/authnz-unittest',
                None,
                'kmsauth-unittest',
                'us-east-1',
                # minimum can't be greater than maximum
                minimum_token_version=2,
                maximum_token_version=1
            )
        assert(kmsauth.KMSTokenValidator(
            'alias/authnz-unittest',
            None,
            'kmsauth-unittest',
            'us-east-1'
        ))

    def test__get_key_arn(self):
        validator = kmsauth.KMSTokenValidator(
            'alias/authnz-unittest',
            None,
            'kmsauth-unittest',
            'us-east-1'
        )
        validator.kms_client = MagicMock()
        validator.KEY_METADATA = {}
        validator.kms_client.describe_key.return_value = {
            'KeyMetadata': {'Arn': 'mocked:arn'}
        }
        self.assertEqual(
            validator._get_key_arn('mockalias'),
            'mocked:arn'
        )

    def test__get_key_arn_cached(self):
        validator = kmsauth.KMSTokenValidator(
            'alias/authnz-unittest',
            None,
            'kmsauth-unittest',
            'us-east-1'
        )
        validator.kms_client = MagicMock()
        validator.KEY_METADATA = {
            'mockalias': {'KeyMetadata': {'Arn': 'mocked:arn'}}
        }
        self.assertEqual(
            validator._get_key_arn('mockalias'),
            'mocked:arn'
        )

    def test__valid_service_auth_key(self):
        validator = kmsauth.KMSTokenValidator(
            'alias/authnz-unittest',
            None,
            'kmsauth-unittest',
            'us-east-1'
        )
        validator._get_key_arn = MagicMock()
        # Test AUTH_KEY arn checking
        validator._get_key_arn.side_effect = ['test::arn']
        self.assertTrue(validator._valid_service_auth_key('test::arn'))

        validator = kmsauth.KMSTokenValidator(
            'alias/authnz-unittest',
            None,
            'kmsauth-unittest',
            'us-east-1',
            scoped_auth_keys={'test-key': 'test-account'}
        )
        validator._get_key_arn = MagicMock()
        # Test SCOPED_AUTH_KEYS arn checking. There's two items in the side
        # effect because get_key_arn will be called twice: once for AUTH_KEY
        # check (which will fail) and another for the SCOPED_AUTH_KEYS check.
        validator._get_key_arn.side_effect = [
            'auth::key',
            'test::arn'
        ]
        self.assertTrue(validator._valid_service_auth_key('test::arn'))
        # Test failure mode, where both AUTH_KEY and SCOPED_AUTH_KEYS checks
        # fail. We have two items in side effects because get_key_arn will be
        # called twice.
        validator._get_key_arn.side_effect = ['auth::key', 'test::arn']
        self.assertFalse(validator._valid_service_auth_key('bad::arn'))

    def test__valid_user_auth_key(self):
        validator = kmsauth.KMSTokenValidator(
            None,
            'alias/authnz-user-unittest',
            'kmsauth-unittest',
            'us-east-1'
        )
        validator._get_key_arn = MagicMock()
        # Test USER_AUTH_KEY arn checking
        validator._get_key_arn.return_value = 'test::arn'
        self.assertTrue(validator._valid_user_auth_key('test::arn'))
        self.assertFalse(validator._valid_service_auth_key('bad::arn'))

    def test__parse_username(self):
        validator = kmsauth.KMSTokenValidator(
            None,
            'alias/authnz-user-unittest',
            'kmsauth-unittest',
            'us-east-1'
        )
        self.assertEqual(
            validator._parse_username('kmsauth-unittest'),
            (1, 'service', 'kmsauth-unittest')
        )
        self.assertEqual(
            validator._parse_username('2/service/kmsauth-unittest'),
            (2, 'service', 'kmsauth-unittest')
        )
        with self.assertRaisesRegexp(
                kmsauth.TokenValidationError,
                'Unsupported username format.'):
            validator._parse_username('3/service/kmsauth-unittest/extratoken')

    def test_decrypt_token(self):
        validator = kmsauth.KMSTokenValidator(
            'alias/authnz-unittest',
            'alias/authnz-user-unittest',
            'kmsauth-unittest',
            'us-east-1'
        )
        validator._get_key_arn = MagicMock(return_value='mocked')
        validator._get_key_alias_from_cache = MagicMock(
            return_value='authnz-testing'
        )
        time_format = "%Y%m%dT%H%M%SZ"
        now = datetime.datetime.utcnow()
        not_before = now.strftime(time_format)
        _not_after = now + datetime.timedelta(minutes=60)
        not_after = _not_after.strftime(time_format)
        payload = json.dumps({
            'not_before': not_before,
            'not_after': not_after
        })
        validator.kms_client.decrypt = MagicMock()
        validator.kms_client.decrypt.return_value = {
            'Plaintext': payload,
            'KeyId': 'mocked'
        }
        # Ensure decrypt succeeds and payload and key alias are the mocked
        # values using v1 token.
        self.assertEqual(
            validator.decrypt_token(
                'kmsauth-unittest',
                'ZW5jcnlwdGVk'
            ),
            {
                'payload': json.loads(payload),
                'key_alias': 'authnz-testing'
            }
        )
        # Ensure decrypt succeeds and payload and key alias are the mocked
        # values using v2 token.
        validator.TOKENS = lru.LRUCache(4096)
        self.assertEqual(
            validator.decrypt_token(
                '2/user/testuser',
                'ZW5jcnlwdGVk'
            ),
            {
                'payload': json.loads(payload),
                'key_alias': 'authnz-testing'
            }
        )
        # Ensure we check token version
        validator.TOKENS = lru.LRUCache(4096)
        with self.assertRaisesRegexp(
                kmsauth.TokenValidationError,
                'Unacceptable token version.'):
            validator.decrypt_token(
                '3/user/testuser',
                'ZW5jcnlwdGVk'
            )
        # Ensure we check user types
        with self.assertRaisesRegexp(
                kmsauth.TokenValidationError,
                'Authentication error. Unsupported user_type.'):
            validator.decrypt_token(
                '2/unsupported/testuser',
                'ZW5jcnlwdGVk'
            )
        # Missing KeyId, will cause an exception to be thrown
        validator.kms_client.decrypt.return_value = {
            'Plaintext': payload
        }
        with self.assertRaisesRegexp(
                kmsauth.TokenValidationError,
                'Authentication error. General error.'):
            validator.decrypt_token(
                '2/service/kmsauth-unittest',
                'ZW5jcnlwdGVk'
            )
        # Payload missing not_before/not_after
        empty_payload = json.dumps({})
        validator.kms_client.decrypt.return_value = {
            'Plaintext': empty_payload,
            'KeyId': 'mocked'
        }
        with self.assertRaisesRegexp(
                kmsauth.TokenValidationError,
                'Authentication error. Missing validity.'):
            validator.decrypt_token(
                '2/service/kmsauth-unittest',
                'ZW5jcnlwdGVk'
            )
        # lifetime of 0 will make every token invalid. testing for proper delta
        # checking.
        validator = kmsauth.KMSTokenValidator(
            'alias/authnz-unittest',
            'alias/authnz-user-unittest',
            'kmsauth-unittest',
            'us-east-1',
            auth_token_max_lifetime=0
        )
        validator._get_key_arn = MagicMock(return_value='mocked')
        validator._get_key_alias_from_cache = MagicMock(
            return_value='authnz-testing'
        )
        validator.kms_client.decrypt = MagicMock()
        validator.kms_client.decrypt.return_value = {
            'Plaintext': payload,
            'KeyId': 'mocked'
        }
        with self.assertRaisesRegexp(
                kmsauth.TokenValidationError,
                'Authentication error. Token lifetime exceeded.'):
            validator.decrypt_token(
                '2/service/kmsauth-unittest',
                'ZW5jcnlwdGVk'
            )
        # Token too old
        validator = kmsauth.KMSTokenValidator(
            'alias/authnz-unittest',
            'alias/authnz-user-unittest',
            'kmsauth-unittest',
            'us-east-1'
        )
        validator._get_key_arn = MagicMock(return_value='mocked')
        validator._get_key_alias_from_cache = MagicMock(
            return_value='authnz-testing'
        )
        now = datetime.datetime.utcnow()
        _not_before = now - datetime.timedelta(minutes=60)
        not_before = _not_before.strftime(time_format)
        _not_after = now - datetime.timedelta(minutes=1)
        not_after = _not_after.strftime(time_format)
        payload = json.dumps({
            'not_before': not_before,
            'not_after': not_after
        })
        validator.kms_client.decrypt = MagicMock()
        validator.kms_client.decrypt.return_value = {
            'Plaintext': payload,
            'KeyId': 'mocked'
        }
        with self.assertRaisesRegexp(
                kmsauth.TokenValidationError,
                'Authentication error. Invalid time validity for token.'):
            validator.decrypt_token(
                '2/service/kmsauth-unittest',
                'ZW5jcnlwdGVk'
            )
        # Token too young
        now = datetime.datetime.utcnow()
        _not_before = now + datetime.timedelta(minutes=60)
        not_before = _not_before.strftime(time_format)
        _not_after = now + datetime.timedelta(minutes=120)
        not_after = _not_after.strftime(time_format)
        payload = json.dumps({
            'not_before': not_before,
            'not_after': not_after
        })
        validator.kms_client.decrypt.return_value = {
            'Plaintext': payload,
            'KeyId': 'mocked'
        }
        with self.assertRaisesRegexp(
                kmsauth.TokenValidationError,
                'Authentication error. Invalid time validity for token'):
            validator.decrypt_token(
                '2/service/kmsauth-unittest',
                'ZW5jcnlwdGVk'
            )


class KMSTokenGeneratorTest(unittest.TestCase):

    @patch(
        'kmsauth.services.get_boto_client',
        MagicMock()
    )
    def test_validate_config(self):
        with self.assertRaises(kmsauth.ConfigurationError):
            kmsauth.KMSTokenGenerator(
                'alias/authnz-unittest',
                # Missing auth context. This causes a validation error
                {},
                'us-east-1'
            )
        with self.assertRaises(kmsauth.ConfigurationError):
            kmsauth.KMSTokenGenerator(
                'alias/authnz-unittest',
                # Missing user_type context. This causes a validation error
                {'from': 'test', 'to': 'test'},
                'us-east-1'
            )
        with self.assertRaises(kmsauth.ConfigurationError):
            kmsauth.KMSTokenGenerator(
                'alias/authnz-unittest',
                {'from': 'test', 'to': 'test', 'user_type': 'user'},
                'us-east-1',
                # invalid token version
                token_version=3
            )
        assert(kmsauth.KMSTokenGenerator(
            'alias/authnz-unittest',
            {'from': 'test', 'to': 'test'},
            'us-east-1',
            token_version=1
        ))
        assert(kmsauth.KMSTokenGenerator(
            'alias/authnz-unittest',
            {'from': 'test', 'to': 'test', 'user_type': 'user'},
            'us-east-1',
            token_version=2
        ))

    @patch(
        'kmsauth.services.get_boto_client',
        MagicMock()
    )
    def test_get_username(self):
        client = kmsauth.KMSTokenGenerator(
            'alias/authnz-testing',
            {'from': 'kmsauth-unittest', 'to': 'test'},
            'us-east-1',
            token_version=1
        )
        self.assertEqual(
            client.get_username(),
            'kmsauth-unittest'
        )
        client = kmsauth.KMSTokenGenerator(
            'alias/authnz-testing',
            {'from': 'kmsauth-unittest',
             'to': 'test',
             'user_type': 'service'},
            'us-east-1',
            token_version=2
        )
        self.assertEqual(
            client.get_username(),
            '2/service/kmsauth-unittest'
        )

    @patch(
        'kmsauth.services.get_boto_client'
    )
    def test_get_token(self, boto_mock):
        kms_mock = MagicMock()
        kms_mock.encrypt = MagicMock(
            return_value={'CiphertextBlob': 'encrypted'}
        )
        boto_mock.return_value = kms_mock
        client = kmsauth.KMSTokenGenerator(
            'alias/authnz-testing',
            {'from': 'kmsauth-unittest',
             'to': 'test',
             'user_type': 'service'},
            'us-east-1'
        )
        token = client.get_token()
        self.assertEqual(token, base64.b64encode(b'encrypted'))
