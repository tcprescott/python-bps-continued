#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

import unittest
from io import BytesIO, StringIO
from blip import constants as C
from blip.io import read_blip, write_blip, read_blip_asm, write_blip_asm
from blip.test.util import find_blip, find_blipa


class TestIO(unittest.TestCase):

	def _runtests(self, name, eventlist):
		"""
		Test the various interactions for a given patch.
		"""
		# Test that we can write the asm version of the patch.
		out_buf = StringIO()
		write_blip_asm(eventlist, out_buf)
		self.assertMultiLineEqual(out_buf.getvalue(), find_blipa(name))

		# Test that we can read the asm version of the patch.
		in_buf = StringIO(find_blipa(name))
		items = list(read_blip_asm(in_buf))

		self.assertSequenceEqual(eventlist, items)

		# Test that we can write the binary patch.
		out_buf = BytesIO()
		write_blip(eventlist, out_buf)
		self.assertSequenceEqual(out_buf.getvalue(), find_blip(name))

		# Test that we can read the binary patch.
		in_buf = BytesIO(find_blip(name))
		items = list(read_blip(in_buf))

		self.assertSequenceEqual(eventlist, items)

		# Test that we can roundtrip the binary version through our reader and
		# writer.
		original = BytesIO(find_blip(name))
		events = read_blip(original)
		output = BytesIO()
		write_blip(events, output)

		self.assertSequenceEqual(original.getvalue(), output.getvalue())

		# Test that we can roundtrip the asm version through our reader and
		# writer.
		original = StringIO(find_blipa(name))
		events = read_blip_asm(original)
		output = StringIO()
		write_blip_asm(events, output)

		self.assertMultiLineEqual(original.getvalue(), output.getvalue())

	def testEmptyPatch(self):
		"""
		The simplest possible patch can be processed correctly.
		"""
		self._runtests("empty", [
				(C.BLIP_MAGIC, 0, 0, ""),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			])

	def testPatchWithMetadata(self):
		"""
		We can process a patch with metadata.
		"""
		self._runtests("metadata", [
				(C.BLIP_MAGIC, 0, 0,
					'<test>\n. leading "." is escaped\n</test>\n'),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			])

	def testPatchWithSourceRead(self):
		"""
		We can process a patch with a SourceRead opcode.
		"""
		self._runtests("sourceread", [
				(C.BLIP_MAGIC, 1, 1, ""),
				(C.SOURCEREAD, 1),
				# For the CRC32 to be correct, the one byte must be b'A'
				(C.SOURCECRC32, 0xD3D99E8B),
				(C.TARGETCRC32, 0xD3D99E8B),
			])

	def testPatchWithTargetRead(self):
		"""
		We can process a patch with a TargetRead opcode.
		"""
		self._runtests("targetread", [
				(C.BLIP_MAGIC, 0, 1, ""),
				(C.TARGETREAD, b'A'),
				(C.SOURCECRC32, 0x00000000),
				(C.TARGETCRC32, 0xD3D99E8B),
			])

	def testPatchWithSourceCopy(self):
		"""
		We can process a patch with a SourceCopy opcode.
		"""
		self._runtests("sourcecopy", [
				(C.BLIP_MAGIC, 2, 2, ""),
				# We copy the second byte in the source file.
				(C.SOURCECOPY, 1, 1),
				# We copy the first byte in the source file.
				(C.SOURCECOPY, 1, 0),
				# This CRC32 represents b'AB'
				(C.SOURCECRC32, 0x30694C07),
				# This CRC32 represents b'BA'
				(C.TARGETCRC32, 0x824D4E7E),
			])

	def testPatchWithTargetCopy(self):
		"""
		We can process a patch with a TargetCopy opcode.
		"""
		self._runtests("targetcopy", [
				(C.BLIP_MAGIC, 0, 4, ""),
				# Add a TargetRead opcode, so TargetCopy has something to copy.
				(C.TARGETREAD, b'A'),
				# Add a TargetCopy opcode that does the RLE trick of reading
				# more data than is currently written.
				(C.TARGETCOPY, 2, 0),
				# Add a TargetCopy that seeks to an earlier offset, so we make
				# sure negative offsets are handled correctly.
				(C.TARGETCOPY, 1, 0),
				# This CRC32 represents b''
				(C.SOURCECRC32, 0x00000000),
				# This CRC32 represents b'AAAA'
				(C.TARGETCRC32, 0x9B0D08F1),
			])


if __name__ == "__main__":
	unittest.main()
