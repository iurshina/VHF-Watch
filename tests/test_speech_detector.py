"""Unit tests for the SpeechDetector class and its model download logic."""
import unittest
from unittest.mock import patch, call, MagicMock
import os
import urllib.request

# Attempt to import SpeechDetector and its constants
# This might require adjusting sys.path if tests are run from a top-level directory
# For now, assume it can be found or will be adjusted in the test runner environment
from vhf_watch.recorder.speech_detector import SpeechDetector, SILERO_VAD_DIR, SILERO_MODEL_FILES, SILERO_REPO_URL
from vhf_watch.logger_config import setup_logger # SpeechDetector uses this

# Mock torch before SpeechDetector tries to import it in its __init__
# This is to prevent actual torch.hub.load calls during unit testing of _ensure_silero_model_present
MOCK_TORCH_HUB = MagicMock()

class TestSpeechDetector(unittest.TestCase):

    @patch('torch.hub.load', MOCK_TORCH_HUB) # Mock torch.hub.load for all tests in this class
    @patch('urllib.request.urlretrieve')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_model_files_already_exist(self, mock_exists, mock_makedirs, mock_urlretrieve, mock_torch_hub_load_method):
        # Setup: os.path.exists returns True for all model files
        mock_exists.return_value = True

        # Action: Instantiate SpeechDetector
        # The _ensure_silero_model_present method is called during __init__
        detector = SpeechDetector()

        # Assertions
        # 1. os.makedirs was called to ensure directory exists
        mock_makedirs.assert_called_once_with(SILERO_VAD_DIR, exist_ok=True)

        # 2. os.path.exists was called for each model file
        expected_exists_calls = []
        for model_file in SILERO_MODEL_FILES:
            expected_exists_calls.append(call(os.path.join(SILERO_VAD_DIR, model_file)))
        mock_exists.assert_has_calls(expected_exists_calls, any_order=False) # Order matters here for the check logic

        # 3. urllib.request.urlretrieve was NOT called
        mock_urlretrieve.assert_not_called()

        # 4. torch.hub.load was called correctly (after checks)
        mock_torch_hub_load_method.assert_called_once_with(
            SILERO_VAD_DIR,
            'silero_vad',
            source='local',
            trust_repo=True
        )

        # Check that the logger was used (optional, but good for completeness)
        # This requires capturing log messages, which can be complex with unittest.
        # For now, focusing on the direct interactions.

    @patch('torch.hub.load', MOCK_TORCH_HUB) # Mock torch.hub.load
    @patch('urllib.request.urlretrieve')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_model_files_downloaded_successfully(self, mock_exists, mock_makedirs, mock_urlretrieve, mock_torch_hub_load_method):
        # Setup:
        # os.path.exists returns False for all files, indicating they are not present locally.
        mock_exists.return_value = False
        # urllib.request.urlretrieve does nothing (simulates successful download)
        mock_urlretrieve.return_value = None

        # Action: Instantiate SpeechDetector
        detector = SpeechDetector()

        # Assertions
        # 1. os.makedirs was called
        mock_makedirs.assert_called_once_with(SILERO_VAD_DIR, exist_ok=True)

        # 2. os.path.exists was called multiple times:
        #    - First for the initial check (all False)
        #    - Then again inside the download loop for each file (all False before download)
        expected_exists_calls = []
        # Initial check in _ensure_silero_model_present (breaks on first False)
        expected_exists_calls.append(call(os.path.join(SILERO_VAD_DIR, SILERO_MODEL_FILES[0])))
        # Checks inside the loop before downloading each file
        for model_file in SILERO_MODEL_FILES:
            expected_exists_calls.append(call(os.path.join(SILERO_VAD_DIR, model_file)))

        # This assertion needs to be flexible because the loop might call exists for all files,
        # or break after the first one in the initial check.
        # For simplicity, let's check the calls for the download part.
        # The first call in the initial check is to the first file.
        self.assertIn(call(os.path.join(SILERO_VAD_DIR, SILERO_MODEL_FILES[0])), mock_exists.call_args_list)
        # Then, for each file, it's checked again before download.
        for model_file in SILERO_MODEL_FILES:
            self.assertIn(call(os.path.join(SILERO_VAD_DIR, model_file)), mock_exists.call_args_list)


        # 3. urllib.request.urlretrieve was called for each model file
        expected_urlretrieve_calls = []
        for model_file in SILERO_MODEL_FILES:
            expected_url_ = SILERO_REPO_URL + model_file
            expected_local_path = os.path.join(SILERO_VAD_DIR, model_file)
            expected_urlretrieve_calls.append(call(expected_url_, expected_local_path))
        mock_urlretrieve.assert_has_calls(expected_urlretrieve_calls, any_order=False) # Order should be preserved

        # 4. torch.hub.load was called correctly
        mock_torch_hub_load_method.assert_called_once_with(
            SILERO_VAD_DIR,
            'silero_vad',
            source='local',
            trust_repo=True
        )

    @patch('torch.hub.load', MOCK_TORCH_HUB) # Mock torch.hub.load
    @patch('urllib.request.urlretrieve')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_model_download_fails(self, mock_exists, mock_makedirs, mock_urlretrieve, mock_torch_hub_load_method):
        # Setup:
        # os.path.exists returns False, indicating files are not present.
        mock_exists.return_value = False
        # urllib.request.urlretrieve raises a URLError on the first attempt.
        mock_urlretrieve.side_effect = urllib.error.URLError("Simulated download failure")

        # Action & Assertion:
        # Expect a RuntimeError to be raised when SpeechDetector is instantiated.
        with self.assertRaises(RuntimeError) as context:
            SpeechDetector()

        # Optional: Check the error message if needed
        self.assertTrue("Failed to download critical Silero VAD model file" in str(context.exception))

        # Assertions
        # 1. os.makedirs was called
        mock_makedirs.assert_called_once_with(SILERO_VAD_DIR, exist_ok=True)

        # 2. os.path.exists was called for the first file (at least)
        mock_exists.assert_any_call(os.path.join(SILERO_VAD_DIR, SILERO_MODEL_FILES[0]))

        # 3. urllib.request.urlretrieve was called for the first file
        first_model_file = SILERO_MODEL_FILES[0]
        expected_url_ = SILERO_REPO_URL + first_model_file
        expected_local_path = os.path.join(SILERO_VAD_DIR, first_model_file)
        mock_urlretrieve.assert_called_once_with(expected_url_, expected_local_path)

        # 4. torch.hub.load was NOT called because the process should have exited.
        mock_torch_hub_load_method.assert_not_called()

if __name__ == '__main__':
    unittest.main()
