#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

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
