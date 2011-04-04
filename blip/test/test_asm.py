#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

import unittest
from io import BytesIO, StringIO
from blip import asm
from blip.test.util import find_blip, find_blipa


class TestDisassembler(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		The simplest possible patch should be disassembled correctly.
		"""
		in_buf = BytesIO(find_blip("empty"))
		out_buf = StringIO()
		asm.disassemble(in_buf, out_buf)
		self.assertMultiLineEqual(out_buf.getvalue(), find_blipa("empty"))

	def testPatchWithMetadata(self):
		"""
		We correctly disassemble a patch with metadata.
		"""
		in_buf = BytesIO(find_blip("metadata"))
		out_buf = StringIO()
		asm.disassemble(in_buf, out_buf)
		self.assertMultiLineEqual(out_buf.getvalue(), find_blipa("metadata"))


class TestAssembler(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		The simplest possible patch should be assembled correctly.
		"""
		in_buf = StringIO(find_blipa("empty"))
		out_buf = BytesIO()
		asm.assemble(in_buf, out_buf)
		self.assertSequenceEqual(out_buf.getvalue(), find_blip("empty"))

	def testPatchWithMetadata(self):
		"""
		We correctly construct a patch with metadata.
		"""
		in_buf = StringIO(find_blipa("metadata"))
		out_buf = BytesIO()
		asm.assemble(in_buf, out_buf)
		self.assertSequenceEqual(out_buf.getvalue(), find_blip("metadata"))


if __name__ == "__main__":
	unittest.main()
