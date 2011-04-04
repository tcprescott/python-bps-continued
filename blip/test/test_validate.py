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
from blip.validate import check_stream, CorruptFile


class TestCheckStream(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		The simplest possible patch does not cause an error.
		"""
		original = [
				(C.BLIP_MAGIC, 0, 0, ""),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]

		self.assertSequenceEqual(original, list(check_stream(original)))

	def testHeaderChecking(self):
		"""
		Raise CorruptFile if the header has any problems.
		"""
		# Header chunk must have exactly 4 items.
		self.assertRaisesRegexp(CorruptFile, "bad header", list,
				check_stream([(C.BLIP_MAGIC, 0, "")]))
		self.assertRaisesRegexp(CorruptFile, "bad header", list,
				check_stream([(C.BLIP_MAGIC, 0, 0, 0, "")]))

		# Magic number must be a bytes object.
		self.assertRaisesRegexp(CorruptFile, "must be bytes", list,
				check_stream([("blip", 0, 0, "")]))

		# A bad value for the magic number raises an exception.
		self.assertRaisesRegexp(CorruptFile, "bad magic", list,
				check_stream([(b"sasquatch", 0, 0, "")]))

		# File lengths must be integers
		self.assertRaisesRegexp(CorruptFile, "not a valid integer", list,
				check_stream([(C.BLIP_MAGIC, "foo", 0, "")]))
		self.assertRaisesRegexp(CorruptFile, "not a valid integer", list,
				check_stream([(C.BLIP_MAGIC, 0, "bar", "")]))

		# File lengths must be positive
		self.assertRaisesRegexp(CorruptFile, "at least zero", list,
				check_stream([(C.BLIP_MAGIC, -37, 0, "")]))
		self.assertRaisesRegexp(CorruptFile, "at least zero", list,
				check_stream([(C.BLIP_MAGIC, 0, -23, "")]))

		# Metadata must be a string.
		self.assertRaisesRegexp(CorruptFile, "must be a string", list,
				check_stream([(C.BLIP_MAGIC, 0, 0, b"")]))

	def testUnrecognisedOpcode(self):
		"""
		Raise CorruptFile if there's an item with an unknown opcode.
		"""
		self.assertRaisesRegexp(CorruptFile, "unknown opcode", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(b'sasquatch', 42),
				])
			)

	def testSourceReadOpcode(self):
		"""
		Raise CorruptFile if a SourceRead opcode has any problems.
		"""
		# SourceRead requires exactly one parameter.
		self.assertRaisesRegexp(CorruptFile, "requires 1 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCEREAD,),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "requires 1 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCEREAD, 1, 2),
				])
			)

		# Length must be an integer
		self.assertRaisesRegexp(CorruptFile, "not a valid integer", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCEREAD, "foo"),
				])
			)

		# Length must be positive.
		self.assertRaisesRegexp(CorruptFile, "greater than zero", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCEREAD, -1),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "greater than zero", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCEREAD, 0),
				])
			)

		# Can read right up to the end of the source file.
		original = [
				(C.BLIP_MAGIC, 5, 5, ""),
				(C.SOURCEREAD, 5),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

		# Can't read past the end of the source file.
		self.assertRaisesRegexp(CorruptFile, "end of the source", list,
				check_stream([
					(C.BLIP_MAGIC, 5, 6, ""),
					# Read part of the source file.
					(C.SOURCEREAD, 1),
					# Trying to read past the end of the source file.
					(C.SOURCEREAD, 5),
				])
			)

	def testTargetReadOpcode(self):
		"""
		Raise CorruptFile if a SourceRead opcode has any problems.
		"""
		# TargetRead requires exactly one parameter.
		self.assertRaisesRegexp(CorruptFile, "requires 1 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETREAD,),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "requires 1 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETREAD, 1, 2),
				])
			)

		# TargetRead's parameter must be bytes.
		self.assertRaisesRegexp(CorruptFile, "must be bytes", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETREAD, 1),
				])
			)

		# TargetRead's parameter must be non-empty.
		self.assertRaisesRegexp(CorruptFile, "must not be empty", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETREAD, b''),
				])
			)

	def testSourceCopyOpcode(self):
		"""
		Raise CorruptFile if a SourceCopy opcode has any problems.
		"""
		# SourceCopy requires exactly two parameters.
		self.assertRaisesRegexp(CorruptFile, "requires 2 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCECOPY, 1),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "requires 2 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCECOPY, 1, 2, 3),
				])
			)

		# Length must be an integer
		self.assertRaisesRegexp(CorruptFile, "not a valid integer", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCECOPY, "foo", 0),
				])
			)

		# Length must be positive.
		self.assertRaisesRegexp(CorruptFile, "greater than zero", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCECOPY, -1, 0),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "greater than zero", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCECOPY, 0, 0),
				])
			)

		# Offset must be an integer
		self.assertRaisesRegexp(CorruptFile, "not a valid integer", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 1, ""),
					(C.SOURCECOPY, 1, "foo"),
				])
			)

	def testSourceCopyLimits(self):
		"""
		Raise CorruptFile if SourceCopy tries to copy from outside the file.
		"""
		# sourceRelativeOffset starts at 0, we should complain if the first
		# SourceCopy has an offset < 0
		self.assertRaisesRegexp(CorruptFile, "beginning of the source", list,
				check_stream([
					(C.BLIP_MAGIC, 1, 2, ""),
					(C.SOURCECOPY, 2, -1),
				])
			)

		# An offset of 0 should be fine, however.
		original = [
				(C.BLIP_MAGIC, 2, 2, ""),
				(C.SOURCECOPY, 2, 0),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

		# After the first SourceCopy, sourceRelativeOffset has increased by the
		# the SourceCopy's length, so we can use a negative offset.
		original = [
				(C.BLIP_MAGIC, 1, 2, ""),
				(C.SOURCECOPY, 1, 0),
				(C.SOURCECOPY, 1, -1),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

		# Likewise, sourceRelativeOffset + offset + length must be at most
		# sourceSize.
		original = [
				(C.BLIP_MAGIC, 2, 2, ""),
				# sourceRelativeOffset is 0
				(C.SOURCECOPY, 1, 0),
				# sourceRelativeOffset is now 1.
				# sourceRelativeOffset + offset + length = sourceSize, so this
				# should be OK.
				(C.SOURCECOPY, 1, 0),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

		# Here we read past the end of the source, which should raise an
		# exception.
		self.assertRaisesRegexp(CorruptFile, "end of the source", list,
				check_stream([
					(C.BLIP_MAGIC, 2, 3, ""),
					(C.SOURCECOPY, 1, 0),
					(C.SOURCECOPY, 1, 1),
				])
			)

	def testTargetCopyOpcode(self):
		"""
		Raise CorruptFile if a TargetCopy opcode has any problems.
		"""
		# SourceCopy requires exactly two parameters.
		self.assertRaisesRegexp(CorruptFile, "requires 2 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETCOPY, 1),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "requires 2 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETCOPY, 1, 2, 3),
				])
			)

		# Length must be an integer
		self.assertRaisesRegexp(CorruptFile, "not a valid integer", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETCOPY, "foo", 0),
				])
			)

		# Length must be positive.
		self.assertRaisesRegexp(CorruptFile, "greater than zero", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETCOPY, -1, 0),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "greater than zero", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETCOPY, 0, 0),
				])
			)

		# Offset must be an integer
		self.assertRaisesRegexp(CorruptFile, "not a valid integer", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETCOPY, 1, "foo"),
				])
			)

	def testTargetCopyLimits(self):
		"""
		Raise CorruptFile if TargetCopy tries to copy from outside the file.
		"""
		# targetRelativeOffset starts at 0, we should complain if the first
		# TargetCopy has an offset < 0
		self.assertRaisesRegexp(CorruptFile, "beginning of the target", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 2, ""),
					(C.TARGETREAD, b'A'),
					(C.TARGETCOPY, 1, -1),
				])
			)

		# An offset of 0 should be fine, however.
		original = [
				(C.BLIP_MAGIC, 0, 2, ""),
				(C.TARGETREAD, b'A'),
				(C.TARGETCOPY, 1, 0),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

		# After the first TargetCopy, targetRelativeOffset has increased by the
		# copy's length, so we can use a negative offset.
		original = [
				(C.BLIP_MAGIC, 0, 3, ""),
				(C.TARGETREAD, b'A'),
				(C.TARGETCOPY, 1, 0),
				(C.TARGETCOPY, 1, -1),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

		# Likewise, targetRelativeOffset + offset must be less than
		# targetWriteOffset.
		original = [
				(C.BLIP_MAGIC, 0, 3, ""),
				(C.TARGETREAD, b'A'),
				(C.TARGETCOPY, 1, 0),
				# Now targetRelativeOffset = 1 and targetWriteOffset = 2
				(C.TARGETCOPY, 1, 0),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

		# Trying to read the byte that targetWriteOffset is pointing at is not
		# allowed.
		self.assertRaisesRegexp(CorruptFile, "end of the written part", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 5, ""),
					(C.TARGETREAD, b'A'),
					# Now targetRelativeOffset = 1 and targetWriteOffset = 1
					(C.TARGETCOPY, 1, 1),
				])
			)

		# But it's OK if the length goes past targetWriteOffset; that's how RLE
		# works.
		original = [
				(C.BLIP_MAGIC, 0, 5, ""),
				(C.TARGETREAD, b'A'),
				(C.TARGETCOPY, 4, 0),
				(C.SOURCECRC32, 0),
				(C.TARGETCRC32, 0),
			]
		self.assertSequenceEqual(original, list(check_stream(original)))

	def testSourceCRC32Opcoode(self):
		"""
		Raise CorruptFile if a SourceCRC32 opcode has any problems.
		"""
		# SourceCRC32 requires exactly one parameter.
		self.assertRaisesRegexp(CorruptFile, "requires 1 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 0, ""),
					(C.SOURCECRC32,),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "requires 1 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 0, ""),
					(C.SOURCECRC32, 1, 2),
				])
			)

		# CRC32 must be an integer
		self.assertRaisesRegexp(CorruptFile, "not a valid integer", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 0, ""),
					(C.SOURCECRC32, "foo"),
				])
			)

		# CRC32 must be between 0 and 2**32 - 1
		self.assertRaisesRegexp(CorruptFile, "at least zero", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 0, ""),
					(C.SOURCECRC32, -1),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "less than 2\*\*32", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 0, ""),
					(C.SOURCECRC32, 2**32),
				])
			)

	def testTargetCRC32Opcoode(self):
		"""
		Raise CorruptFile if a TargetCRC32 opcode has any problems.
		"""
		# TargetCRC32 requires exactly one parameter.
		self.assertRaisesRegexp(CorruptFile, "requires 1 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 0, ""),
					(C.SOURCECRC32, 0),
					(C.TARGETCRC32,),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "requires 1 parameter", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 0, ""),
					(C.SOURCECRC32, 0),
					(C.TARGETCRC32, 1, 2),
				])
			)

		# CRC32 must be an integer
		self.assertRaisesRegexp(CorruptFile, "not a valid integer", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 0, ""),
					(C.SOURCECRC32, 0),
					(C.TARGETCRC32, "foo"),
				])
			)

		# CRC32 must be between 0 and 2**32 - 1
		self.assertRaisesRegexp(CorruptFile, "at least zero", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 0, ""),
					(C.SOURCECRC32, 0),
					(C.TARGETCRC32, -1),
				])
			)
		self.assertRaisesRegexp(CorruptFile, "less than 2\*\*32", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 0, ""),
					(C.SOURCECRC32, 0),
					(C.TARGETCRC32, 2**32),
				])
			)

	def testWritingPastTheEndOfTheTarget(self):
		"""
		Raise CorruptFile if the patch writes more than targetsize bytes.
		"""
		self.assertRaisesRegexp(CorruptFile, "end of the target", list,
				check_stream([
					(C.BLIP_MAGIC, 5, 1, ""),
					(C.SOURCEREAD, 5),
				])
			)

		self.assertRaisesRegexp(CorruptFile, "end of the target", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETREAD, b'hello'),
				])
			)

		self.assertRaisesRegexp(CorruptFile, "end of the target", list,
				check_stream([
					(C.BLIP_MAGIC, 5, 1, ""),
					(C.SOURCECOPY, 5, 0),
				])
			)

		self.assertRaisesRegexp(CorruptFile, "end of the target", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 2, ""),
					(C.TARGETREAD, b'A'),
					(C.TARGETCOPY, 5, 0),
				])
			)

	def testTruncatedStream(self):
		"""
		Raise CorruptFile if the iterable ends before we have a whole patch.
		"""
		# Complain if there's no header.
		self.assertRaisesRegexp(CorruptFile, "truncated patch", list,
				check_stream([])
			)

		# Complain if there's no patch hunks and there should be.
		self.assertRaisesRegexp(CorruptFile, "truncated patch", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
				])
			)

		# Complain if there's no source CRC32 opcode.
		self.assertRaisesRegexp(CorruptFile, "truncated patch", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETREAD, b'A'),
				])
			)

		# Complain if there's no target CRC32 opcode.
		self.assertRaisesRegexp(CorruptFile, "truncated patch", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETREAD, b'A'),
					(C.SOURCECRC32, 0),
				])
			)

	def testStateMachine(self):
		"""
		Raise CorruptFile if we get valid opcodes out of order.
		"""
		# Complain if we get a SourceCRC32 before any patch hunks.
		self.assertRaisesRegexp(CorruptFile, "unknown opcode", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.SOURCECRC32, 0),
				])
			)

		# Complain if we get a TargetCRC32 before a SourceCRC32 opcode.
		self.assertRaisesRegexp(CorruptFile, "expected sourcecrc32", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETREAD, b'A'),
					(C.TARGETCRC32, 0),
				])
			)

		# Complain if we anything after SourceCRC32 besides TargetCRC32
		self.assertRaisesRegexp(CorruptFile, "expected targetcrc32", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETREAD, b'A'),
					(C.SOURCECRC32, 0),
					(C.TARGETREAD, b'A'),
				])
			)

	def testTrailingGarbage(self):
		"""
		Raise CorruptFile if there's anything after TargetCRC32.
		"""
		self.assertRaisesRegexp(CorruptFile, "trailing garbage", list,
				check_stream([
					(C.BLIP_MAGIC, 0, 1, ""),
					(C.TARGETREAD, b'A'),
					(C.SOURCECRC32, 0),
					(C.TARGETCRC32, 0xD3D99E8B),
					(C.TARGETREAD, b'A'),
				])
			)


if __name__ == "__main__":
	unittest.main()
