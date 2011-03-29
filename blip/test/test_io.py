#!/usr/bin/python3
import unittest
from io import BytesIO, StringIO
from blip import constants as C
from blip.io import read_blip, write_blip, read_blip_asm, write_blip_asm
from blip.test.util import find_blp, find_blpa

EMPTY_PATCH_EVENTS = [
		(C.BLIP_MAGIC, 0, 0, ""),
		(C.SOURCECRC32, 0),
		(C.TARGETCRC32, 0),
	]

METADATA_PATCH_EVENTS = [
	(C.BLIP_MAGIC, 0, 0,
		'<test>\n. leading "." is escaped\n</test>\n'),
	(C.SOURCECRC32, 0),
	(C.TARGETCRC32, 0),
]


class TestReadBlip(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		The simplest possible patch should be read correctly.
		"""
		in_buf = BytesIO(find_blp("empty"))
		items = list(read_blip(in_buf))

		self.assertSequenceEqual(EMPTY_PATCH_EVENTS, items)

	def testPatchWithMetadata(self):
		"""
		We correctly read a patch with metadata.
		"""
		in_buf = BytesIO(find_blp("metadata"))
		items = list(read_blip(in_buf))

		self.assertListEqual(METADATA_PATCH_EVENTS, items)


class TestWriteBlip(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		We can write out the simplest possible patch.
		"""
		out_buf = BytesIO()
		write_blip(EMPTY_PATCH_EVENTS, out_buf)
		self.assertSequenceEqual(out_buf.getvalue(), find_blp("empty"))

	def testPatchWithMetadata(self):
		"""
		We can write out a patch with metadata.
		"""
		out_buf = BytesIO()
		write_blip(METADATA_PATCH_EVENTS, out_buf)
		self.assertSequenceEqual(out_buf.getvalue(), find_blp("metadata"))


class TestRoundtrip(unittest.TestCase):

	def _test_roundtrip(self, name):
		# Test that the Blip patch can round-trip through read_blip and
		# write_blip
		original = BytesIO(find_blp(name))
		events = read_blip(original)
		output = BytesIO()
		write_blip(events, output)

		self.assertSequenceEqual(original.getvalue(), output.getvalue())

		# Test that the Blip assembler version can round-trip through
		# read_blip_asm and write_blip_asm.
		original = StringIO(find_blpa(name))
		events = read_blip_asm(original)
		output = StringIO()
		write_blip_asm(events, output)

		self.assertMultiLineEqual(original.getvalue(), output.getvalue())

	def testEmptyPatch(self):
		"""
		The simplest possible patch can be read and written without error.
		"""
		self._test_roundtrip("empty")

	def testPatchWithMetadata(self):
		"""
		We can read and write a patch with metadata.
		"""
		self._test_roundtrip("metadata")


class TestReadBlipAsm(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		The simplest possible patch should be read correctly.
		"""
		in_buf = StringIO(find_blpa("empty"))
		items = list(read_blip_asm(in_buf))

		self.assertSequenceEqual(EMPTY_PATCH_EVENTS, items)

	def testPatchWithMetadata(self):
		"""
		We correctly read a patch with metadata.
		"""
		in_buf = StringIO(find_blpa("metadata"))
		items = list(read_blip_asm(in_buf))

		self.assertListEqual(METADATA_PATCH_EVENTS, items)

if __name__ == "__main__":
	unittest.main()
