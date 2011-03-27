#!/usr/bin/python3
import unittest
from io import BytesIO, StringIO
from pkgutil import get_data
from blip import asm

def read_blp(name):
	"""
	Reads a Blip patch from the test data directory.
	"""
	return get_data("blip.test", "testdata/{0}.blp".format(name))


def read_blpa(name):
	"""
	Reads a Blip assembler file from the test data directory.
	"""
	rawdata = get_data("blip.test", "testdata/{0}.blpa".format(name))
	return rawdata.decode("utf-8")


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
