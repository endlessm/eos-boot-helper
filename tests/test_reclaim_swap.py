#!/usr/bin/python3
'''
Tests eos-reclaim-swap.
'''

import contextlib
import os
import subprocess

from .util import (
    BaseTestCase,
    system_script
)


EOS_RECLAIM_SWAP = system_script('eos-reclaim-swap')
DATA_DIR = os.path.dirname(os.path.realpath(__file__)) + '/data/reclaim-swap'


class TestReclaimSwap(BaseTestCase):

    def get_data(self, basename):
        '''
        Return contents of file at DATA_DIR/basename.
        '''
        path = os.path.join(DATA_DIR, basename)
        with open(path, 'rb') as f:
            data = f.read()
        return data

    @contextlib.contextmanager
    def dup_image(self, testname):
        '''
        Return a copy of DATA_DIR/testname.img in the current working dir.
        '''
        basename = testname + '.img'
        path = os.path.join(DATA_DIR, basename)
        with open(path, 'rb') as f:
            data = f.read()
        with open(basename, 'wb') as img:
            img.write(data)
            img.flush()
            yield img

    def strip_table_id(self, table):
        '''
        Return a copy of table without the partition table line.
        '''
        lines = table.splitlines(keepends=True)
        out = []
        for line in lines:
            if line.startswith(b'Disk identifier:'):
                continue
            out.append(line)
        return bytes().join(out)

    def run_test(self, test):
        '''
        Execute test.
        '''
        input_table = self.get_data(test + '-input.txt')
        expected_table = self.get_data(test + '-expected.txt')

        with self.dup_image(test) as img:
            table = subprocess.run(['fdisk', '-l', img.name],
                                   stdout=subprocess.PIPE).stdout
            try:
                self.assertEqual(table, input_table)
            except:  # noqa: E722
                print('Unexpected input image with table:\n' + table.decode())
                raise

            subprocess.run([EOS_RECLAIM_SWAP, '-v', '-p', img.name + '3'],
                           check=True)
            table = subprocess.run(['fdisk', '-l', img.name],
                                   stdout=subprocess.PIPE).stdout
        os.remove(img.name)
        try:
            self.assertEqual(self.strip_table_id(table),
                             self.strip_table_id(expected_table))
        except:  # noqa: E722
            print('Expected result:\n' + expected_table.decode())
            raise

    def test_gpt_noop(self):
        self.run_test('gpt-noop')

    def test_gpt_remove_swap(self):
        self.run_test('gpt-remove-swap')

    def test_gpt_remove_swap_preserving_last(self):
        self.run_test('gpt-remove-swap-preserving-last')

    def test_mbr_noop(self):
        self.run_test('mbr-noop')

    def test_mbr_remove_swap(self):
        self.run_test('mbr-remove-swap')

    def test_mbr_remove_swap_preserving_last(self):
        self.run_test('mbr-remove-swap-preserving-last')
