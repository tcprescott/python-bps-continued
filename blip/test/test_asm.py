#!/usr/bin/python3
import unittest
from io import BytesIO, StringIO
from blip import asm
from blip.test.util import read_blp, read_blpa


class TestDisassembler(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		The simplest possible patch should be disassembled correctly.
		"""
		in_buf = BytesIO(read_blp("empty"))
		out_buf = StringIO()
		asm.disassemble(in_buf, out_buf)
		self.assertMultiLineEqual(out_buf.getvalue(), read_blpa("empty"))

	def testPatchWithMetadata(self):
		"""
		We correctly disassemble a patch with metadata.
		"""
		in_buf = BytesIO(read_blp("metadata"))
		out_buf = StringIO()
		asm.disassemble(in_buf, out_buf)
		self.assertMultiLineEqual(out_buf.getvalue(), read_blpa("metadata"))


class TestAssembler(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		The simplest possible patch should be assembled correctly.
		"""
		in_buf = StringIO(read_blpa("empty"))
		out_buf = BytesIO()
		asm.assemble(in_buf, out_buf)
		self.assertSequenceEqual(out_buf.getvalue(), read_blp("empty"))

	def testPatchWithMetadata(self):
		"""
		We correctly construct a patch with metadata.
		"""
		in_buf = StringIO(read_blpa("metadata"))
		out_buf = BytesIO()
		asm.assemble(in_buf, out_buf)
		self.assertSequenceEqual(out_buf.getvalue(), read_blp("metadata"))


if __name__ == "__main__":
	unittest.main()
