#!/usr/bin/python3
import unittest
from blip import diff

class TestIterBlocks(unittest.TestCase):

	def testEmptyString(self):
		blockmap = list(diff.iter_blocks(b''))

		self.assertSequenceEqual([], blockmap)

	def testShortString(self):
		blockmap = list(diff.iter_blocks(b'A'))

		self.assertSequenceEqual([(b'A', 0)], blockmap)

	def testDelimString(self):
		blockmap = list(diff.iter_blocks(b'\n'))

		self.assertSequenceEqual([(b'\n', 0)], blockmap)

	def testMultiBlockString(self):
		blockmap = list(diff.iter_blocks(b'A' * 70 + b'\n' + b'A' * 70))

		self.assertSequenceEqual(
				[
					(b'A' * 64, 0),
					(b'AAAAAA\n', 64),
					(b'A' * 64, 71),
					(b'AAAAAA', 135),
				],
				blockmap,
			)


if __name__ == "__main__":
	unittest.main()
