# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

"""
Functions for applying Blip patches.
"""
from zlib import crc32
from blip import constants as C
from blip.validate import check_stream, CorruptFile
from blip.io import read_blip
from blip.util import op_size


def apply_to_bytearrays(iterable, source_buf, target_buf):
	"""
	Applies the Blip patch from iterable to source_buf, producing target_buf.

	iterable should be an iterable yielding blip patch opcodes, after the
	header.

	source_buf should be a bytes object, or something impersonating one.

	target_buf should be a bytearray object, or something impersonating one.
	"""
	writeOffset = 0

	for item in iterable:
		length = op_size(item)

		if item[0] == C.BLIP_MAGIC:
			# Just the header, nothing for us to do here.
			pass

		elif item[0] == C.SOURCEREAD:
			target_buf[writeOffset:writeOffset+length] = \
					source_buf[writeOffset:writeOffset+length]

		elif item[0] == C.TARGETREAD:
			target_buf[writeOffset:writeOffset+length] = item[1]

		elif item[0] == C.SOURCECOPY:
			offset = item[2]

			target_buf[writeOffset:writeOffset+length] = \
					source_buf[offset:offset+length]

		elif item[0] == C.TARGETCOPY:
			offset = item[2]

			# Because TargetCopy can be used to implement RLE-type compression,
			# we have to copy a byte at a time rather than just slicing
			# target_buf.
			for i in range(length):
				target_buf[writeOffset+i] = target_buf[offset+i]

		elif item[0] == C.SOURCECRC32:
			actual = crc32(source_buf)
			expected = item[1]

			if actual != expected:
				raise CorruptFile("Source file should have CRC32 {0:08X}, "
						"got {1:08X}".format(expected, actual))

		elif item[0] == C.TARGETCRC32:
			actual = crc32(target_buf)
			expected = item[1]

			if actual != expected:
				raise CorruptFile("Target file should have CRC32 {0:08X}, "
						"got {1:08X}".format(expected, actual))

		else:
			raise CorruptFile("unknown opcode: {0!r}".format(item))

		if length:
			writeOffset += length


def apply_to_files(patch, source, target):
	"""
	Applies the Blip patch to the source file, writing to the target file.

	patch should be a file handle containing Blip patch data.

	source should be a readable, binary file handle containing the source data
	for the blip patch.

	target should be a writable, binary file handle, which will contain the
	result of applying the given patch to the given source data.
	"""
	iterable = check_stream(read_blip(patch))
	sourceData = source.read()

	header, sourceSize, targetSize, metadata = next(iterable)

	if sourceSize != len(sourceData):
		raise CorruptFile("Source file must be {sourceSize} bytes, but "
				"{source!r} is {sourceDataLen} bytes.".format(
					sourceSize=sourceSize, source=source,
					sourceDataLen=len(sourceData)))

	targetData = bytearray(targetSize)

	apply_to_bytearrays(iterable, sourceData, targetData)

	assert len(targetData) == targetSize, ("Should have written {0} bytes to "
			"target, not {1}".format(targetSize, len(targetData)))

	target.write(targetData)
