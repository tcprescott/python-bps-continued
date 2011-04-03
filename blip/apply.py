"""
Functions for applying Blip patches.
"""
from zlib import crc32
from blip import constants as C
from blip.validate import check_stream, CorruptFile
from blip.io import read_blip


def apply_to_bytearrays(iterable, source_buf, target_buf):
	"""
	Applies the Blip patch from iterable to source_buf, producing target_buf.

	iterable should be an iterable yielding blip patch opcodes, after the
	header.

	source_buf should be a bytes object, or something impersonating one.

	target_buf should be a bytearray object, or something impersonating one.
	"""
	writeOffset      = 0
	sourceCopyOffset = 0
	targetCopyOffset = 0

	for item in iterable:
		length = 0

		if item[0] == C.BLIP_MAGIC:
			# Just the header, nothing for us to do here.
			pass

		elif item[0] == C.SOURCEREAD:
			length = item[1]
			target_buf[writeOffset:writeOffset+length] = \
					source_buf[writeOffset:writeOffset+length]

		elif item[0] == C.TARGETREAD:
			length = len(item[1])
			target_buf[writeOffset:writeOffset+length] = item[1]

		elif item[0] == C.SOURCECOPY:
			length = item[1]
			sourceCopyOffset += item[2]

			target_buf[writeOffset:writeOffset+length] = \
					source_buf[sourceCopyOffset:sourceCopyOffset+length]

			sourceCopyOffset += length

		elif item[0] == C.TARGETCOPY:
			length = item[1]
			targetCopyOffset += item[2]

			# Because TargetCopy can be used to implement RLE-type compression,
			# we have to copy a byte at a time rather than just slicing
			# target_buf.
			for i in range(length):
				b = target_buf[targetCopyOffset]
				target_buf[writeOffset] = b

				writeOffset += 1
				targetCopyOffset += 1

			targetCopyOffset += length

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

		writeOffset += length
