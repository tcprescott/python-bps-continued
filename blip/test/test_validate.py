#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

import unittest
from io import BytesIO, StringIO
from blip import operations as ops
from blip.validate import check_stream, CorruptFile


class TestCheckStream(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		The simplest possible patch does not cause an error.
		"""
		original = [
				ops.Header(0, 0),
				ops.SourceCRC32(0),
				ops.TargetCRC32(0),
			]

		self.assertSequenceEqual(original, list(check_stream(original)))

	def testUnrecognisedOpcode(self):
		"""
		Raise CorruptFile if there's an item with an unknown opcode.
		"""
		self.assertRaisesRegex(CorruptFile, "unknown opcode", list,
				check_stream([
					ops.Header(0, 1),
					b'sasquatch',
				])
			)

	def testSourceReadOpcode(self):
		"""
		Raise CorruptFile if a SourceRead opcode has any problems.
		"""
		# Can read right up to the end of the source file.
		original = [
				ops.Header(5, 5),
				ops.SourceRead(5),
				ops.SourceCRC32(0),
				ops.TargetCRC32(0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

		# Can't read past the end of the source file.
		self.assertRaisesRegex(CorruptFile, "end of the source", list,
				check_stream([
					ops.Header(5, 6),
					# Read part of the source file.
					ops.SourceRead(1),
					# Trying to read past the end of the source file.
					ops.SourceRead(5),
				])
			)

	def testSourceCopyLimits(self):
		"""
		Raise CorruptFile if SourceCopy tries to copy from outside the file.
		"""
		# offset + length must be at most sourceSize.
		original = [
				ops.Header(2, 2),
				# offset + length = sourceSize, so this should be OK.
				ops.SourceCopy(2, 0),
				ops.SourceCRC32(0),
				ops.TargetCRC32(0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

		# Here we read past the end of the source, which should raise an
		# exception.
		self.assertRaisesRegex(CorruptFile, "end of the source", list,
				check_stream([
					ops.Header(2, 3),
					ops.SourceCopy(2, 1),
				])
			)

	def testTargetCopyLimits(self):
		"""
		Raise CorruptFile if TargetCopy tries to copy from outside the file.
		"""
		# offset must be less than targetWriteOffset.
		original = [
				ops.Header(0, 2),
				ops.TargetRead(b'A'),
				ops.TargetCopy(1, 0),
				ops.SourceCRC32(0),
				ops.TargetCRC32(0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

		# Trying to read the byte that targetWriteOffset is pointing at is not
		# allowed.
		self.assertRaisesRegex(CorruptFile, "end of the written part", list,
				check_stream([
					ops.Header(0, 5),
					ops.TargetRead(b'A'),
					ops.TargetCopy(1, 1),
				])
			)

		# But it's OK if the length goes past targetWriteOffset; that's how RLE
		# works.
		original = [
				ops.Header(0, 5),
				ops.TargetRead(b'A'),
				ops.TargetCopy(4, 0),
				ops.SourceCRC32(0),
				ops.TargetCRC32(0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

	def testWritingPastTheEndOfTheTarget(self):
		"""
		Raise CorruptFile if the patch writes more than targetsize bytes.
		"""
		# SourceRead can't write past the end of the target.
		self.assertRaisesRegex(CorruptFile, "end of the target", list,
				check_stream([
					ops.Header(5, 1),
					ops.SourceRead(5),
				])
			)

		# TargetRead can't write past the end of the target.
		self.assertRaisesRegex(CorruptFile, "end of the target", list,
				check_stream([
					ops.Header(0, 1),
					ops.TargetRead(b'hello'),
				])
			)

		# SourceCopy can't write past the end of the target.
		self.assertRaisesRegex(CorruptFile, "end of the target", list,
				check_stream([
					ops.Header(5, 1),
					ops.SourceCopy(5, 0),
				])
			)

		# TargetCopy can't write past the end of the target.
		self.assertRaisesRegex(CorruptFile, "end of the target", list,
				check_stream([
					ops.Header(0, 2),
					ops.TargetRead(b'A'),
					ops.TargetCopy(5, 0),
				])
			)

	def testTruncatedStream(self):
		"""
		Raise CorruptFile if the iterable ends before we have a whole patch.
		"""
		# Complain if there's no header.
		self.assertRaisesRegex(CorruptFile, "truncated patch", list,
				check_stream([])
			)

		# Complain if there's no patch hunks and there should be.
		self.assertRaisesRegex(CorruptFile, "truncated patch", list,
				check_stream([
					ops.Header(0, 1),
				])
			)

		# Complain if there's no source CRC32 opcode.
		self.assertRaisesRegex(CorruptFile, "truncated patch", list,
				check_stream([
					ops.Header(0, 1),
					ops.TargetRead(b'A'),
				])
			)

		# Complain if there's no target CRC32 opcode.
		self.assertRaisesRegex(CorruptFile, "truncated patch", list,
				check_stream([
					ops.Header(0, 1),
					ops.TargetRead(b'A'),
					ops.SourceCRC32(0),
				])
			)

	def testStateMachine(self):
		"""
		Raise CorruptFile if we get valid opcodes out of order.
		"""
		# Complain if we get anything before the header opcode.
		self.assertRaisesRegex(CorruptFile, "expected header", list,
				check_stream([
					ops.SourceRead(1),
				]),
			)

		# Complain if we get a SourceCRC32 before any patch hunks.
		self.assertRaisesRegex(CorruptFile, "unknown opcode", list,
				check_stream([
					ops.Header(0, 1),
					ops.SourceCRC32(0),
				])
			)

		# Complain if we get a TargetCRC32 before a SourceCRC32 opcode.
		self.assertRaisesRegex(CorruptFile, "expected SourceCRC32", list,
				check_stream([
					ops.Header(0, 1),
					ops.TargetRead(b'A'),
					ops.TargetCRC32(0),
				])
			)

		# Complain if we anything after SourceCRC32 besides TargetCRC32
		self.assertRaisesRegex(CorruptFile, "expected TargetCRC32", list,
				check_stream([
					ops.Header(0, 1),
					ops.TargetRead(b'A'),
					ops.SourceCRC32(0),
					ops.TargetRead(b'A'),
				])
			)

		# If we get a completely random operation rather than a CRC32, make
		# sure we complain about the opcode, not the number of arguments (or
		# whatever.
		self.assertRaisesRegex(CorruptFile, "expected SourceCRC32", list,
				check_stream([
					ops.Header(0, 0),
					ops.TargetRead(b'A'),
				])
			)
		self.assertRaisesRegex(CorruptFile, "expected SourceCRC32", list,
				check_stream([
					ops.Header(0, 1),
					ops.TargetRead(b'A'),
					ops.TargetCopy(1, 0),
				])
			)

	def testTrailingGarbage(self):
		"""
		Raise CorruptFile if there's anything after TargetCRC32.
		"""
		self.assertRaisesRegex(CorruptFile, "trailing garbage", list,
				check_stream([
					ops.Header(0, 1),
					ops.TargetRead(b'A'),
					ops.SourceCRC32(0),
					ops.TargetCRC32(0xD3D99E8B),
					ops.TargetRead(b'A'),
				])
			)


if __name__ == "__main__":
	unittest.main()
