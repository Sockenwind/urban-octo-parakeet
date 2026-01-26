import unittest
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
from src import cleaner_core

class TestCleanerCore(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory structure for file scanning/cleaning tests
        self.test_dir = tempfile.mkdtemp()

        # Create some junk files
        self.junk_files = [
            os.path.join(self.test_dir, '.DS_Store'),
            os.path.join(self.test_dir, '._image.jpg'),
            os.path.join(self.test_dir, 'subdir', '.DS_Store'),
            os.path.join(self.test_dir, 'subdir', '._doc.pdf')
        ]

        # Create some good files
        self.good_files = [
            os.path.join(self.test_dir, 'image.jpg'),
            os.path.join(self.test_dir, 'subdir', 'doc.pdf')
        ]

        os.makedirs(os.path.join(self.test_dir, 'subdir'), exist_ok=True)

        for f in self.junk_files + self.good_files:
            with open(f, 'w') as file:
                file.write('test')

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_scan_for_junk(self):
        found_files = list(cleaner_core.scan_for_junk(self.test_dir))
        self.assertEqual(len(found_files), 4)
        for junk in self.junk_files:
            self.assertIn(junk, found_files)
        for good in self.good_files:
            self.assertNotIn(good, found_files)

    def test_clean_files_dry_run(self):
        found_files = list(cleaner_core.scan_for_junk(self.test_dir))
        success, failed = cleaner_core.clean_files(found_files, dry_run=True)

        self.assertEqual(success, 4)
        self.assertEqual(failed, 0)

        # Verify files still exist
        for junk in self.junk_files:
            self.assertTrue(os.path.exists(junk))

    def test_clean_files_execution(self):
        found_files = list(cleaner_core.scan_for_junk(self.test_dir))
        success, failed = cleaner_core.clean_files(found_files, dry_run=False)

        self.assertEqual(success, 4)
        self.assertEqual(failed, 0)

        # Verify junk files are gone
        for junk in self.junk_files:
            self.assertFalse(os.path.exists(junk))

        # Verify good files remain
        for good in self.good_files:
            self.assertTrue(os.path.exists(good))

    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    @patch('os.path.ismount')
    @patch('os.stat')
    def test_get_external_volumes(self, mock_stat, mock_ismount, mock_isdir, mock_exists, mock_listdir):
        # Setup mocks
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_listdir.return_value = ['Macintosh HD', 'USB Drive', 'Network Share']

        # Define stat return values to simulate devices
        # Root device = 1
        # Macintosh HD = 1 (same as root)
        # USB Drive = 2 (different)
        # Network Share = 3 (different)

        root_stat = MagicMock()
        root_stat.st_dev = 1

        mac_hd_stat = MagicMock()
        mac_hd_stat.st_dev = 1

        usb_stat = MagicMock()
        usb_stat.st_dev = 2

        net_stat = MagicMock()
        net_stat.st_dev = 3

        def stat_side_effect(path):
            if path == '/': return root_stat
            if 'Macintosh HD' in path: return mac_hd_stat
            if 'USB Drive' in path: return usb_stat
            if 'Network Share' in path: return net_stat
            return MagicMock()

        mock_stat.side_effect = stat_side_effect
        mock_ismount.return_value = True

        volumes = cleaner_core.get_external_volumes()

        self.assertIn('/Volumes/USB Drive', volumes)
        self.assertIn('/Volumes/Network Share', volumes)
        self.assertNotIn('/Volumes/Macintosh HD', volumes)

if __name__ == '__main__':
    unittest.main()
