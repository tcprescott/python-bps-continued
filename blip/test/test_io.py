#!/usr/bin/python3
import unittest
from io import BytesIO, StringIO
from blip import constants as C
from blip.io import read_blip, write_blip
from blip.test.util import find_blp, find_blpa


class TestReadBlip(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		The simplest possible patch should be read correctly.
		"""
		in_buf = BytesIO(find_blp("empty"))
		items = list(read_blip(in_buf))

		self.assertSequenceEqual([
				(C.BLIP_MAGIC, 0, 0, ""),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			], items)

	def testPatchWithMetadata(self):
		"""
		We correctly read a patch with metadata.
		"""
		in_buf = BytesIO(find_blp("metadata"))
		items = list(read_blip(in_buf))

		self.assertListEqual([
				(C.BLIP_MAGIC, 0, 0,
					'<test>\n. leading "." is escaped\n</test>\n'),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			], items)

class TestWriteBlip(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		We can write out the simplest possible patch.
		"""
		events = [
				(C.BLIP_MAGIC, 0, 0, ""),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]
		out_buf = BytesIO()
		write_blip(events, out_buf)
		self.assertSequenceEqual(out_buf.getvalue(), find_blp("empty"))

	def testPatchWithMetadata(self):
		"""
		We can write out a patch with metadata.
		"""
		events = [
				(C.BLIP_MAGIC, 0, 0,
					'<test>\n. leading "." is escaped\n</test>\n'),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]
		out_buf = BytesIO()
		write_blip(events, out_buf)
		self.assertSequenceEqual(out_buf.getvalue(), find_blp("metadata"))

class TestRoundtrip(unittest.TestCase):

	def _test_roundtrip(self, name):
		original = BytesIO(find_blp(name))
		events = read_blip(original)
		output = BytesIO()
		write_blip(events, output)

		self.assertSequenceEqual(original.getvalue(), output.getvalue())

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

if __name__ == "__main__":
	unittest.main()
