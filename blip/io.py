# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

"""
Tools for reading and writing blip patches.
"""
from struct import pack, unpack
import re
from binascii import b2a_hex, a2b_hex
from blip import util
from blip import constants as C
from blip.validate import CorruptFile, check_stream


NON_HEX_DIGIT_RE = re.compile("[^0-9A-Fa-f]")


def _expect_label(expected, actual):
	if actual != expected:
		raise CorruptFile("Expected {expected:r} field, "
				"not {actual:r}".format(expected=expected, actual=actual))


def _read_multiline_text(in_buf):
	lines = []
	while True:
		line = in_buf.readline()
		if line == ".\n":
			break
		if line.startswith("."): line = line[1:]
		lines.append(line)
	return "".join(lines)


def read_blip(in_buf):
	"""
	Yields Blip patch instructions from the Blip patch in in_buf.

	in_buf should implement io.IOBase, opened in 'rb' mode.
	"""
	# Keep track of the input file's CRC32, so we can check it at the end.
	in_buf = util.CRCIOWrapper(in_buf)

	# header
	magic = in_buf.read(4)

	if magic != C.BLIP_MAGIC:
		raise CorruptFile("File magic should be {expected!r}, got "
				"{actual!r}".format(expected=C.BLIP_MAGIC, actual=magic))

	sourcesize = util.read_var_int(in_buf)
	targetsize = util.read_var_int(in_buf)
	metadatasize = util.read_var_int(in_buf)
	metadata = in_buf.read(metadatasize).decode('utf-8')

	yield (magic, sourcesize, targetsize, metadata)

	targetoffset = 0
	while targetoffset < targetsize:
		value = util.read_var_int(in_buf)
		opcode = value & C.OPCODEMASK
		length = (value >> C.OPCODESHIFT) + 1

		if opcode == C.OP_SOURCEREAD:
			yield (C.SOURCEREAD, length)

		elif opcode == C.OP_TARGETREAD:
			yield (C.TARGETREAD, in_buf.read(length))

		elif opcode == C.OP_SOURCECOPY:
			raw_offset = util.read_var_int(in_buf)
			offset = raw_offset >> 1
			if raw_offset & 1:
				offset = -offset
			yield (C.SOURCECOPY, length, offset)

		elif opcode == C.OP_TARGETCOPY:
			raw_offset = util.read_var_int(in_buf)
			offset = raw_offset >> 1
			if raw_offset & 1:
				offset = -offset
			yield (C.TARGETCOPY, length, offset)


		else:
			raise CorruptFile("Unknown opcode: {opcode:02b}".format(
				opcode=opcode))

		targetoffset += length

	# footer
	yield (C.SOURCECRC32, unpack("I", in_buf.read(4))[0])
	yield (C.TARGETCRC32, unpack("I", in_buf.read(4))[0])

	# Check the patch's CRC32.
	actual = in_buf.crc32
	expected = unpack("I", in_buf.read(4))[0]

	if expected != actual:
		raise CorruptFile("Patch claims its CRC32 is {expected:08X}, but "
				"it's really {actual:08X}".format(
					expected=expected, actual=actual)
			)


def write_blip(iterable, out_buf):
	"""
	Encodes Blip patch instructions from the iterable into a patch in out_buf.

	iterable should yield a sequence of Blip patch instructions.

	out_buf should implement io.IOBase, opened in 'wb' mode.
	"""
	# Make sure we have a sensible stream to write.
	iterable = check_stream(iterable)

	# Keep track of the patch data's CRC32, so we can write it out at the end.
	out_buf = util.CRCIOWrapper(out_buf)

	# header
	(magic, sourcesize, targetsize, metadata) = next(iterable)

	out_buf.write(magic)
	util.write_var_int(sourcesize, out_buf)
	util.write_var_int(targetsize, out_buf)
	metadata = metadata.encode('utf-8')
	util.write_var_int(len(metadata), out_buf)
	out_buf.write(metadata)

	for item in iterable:
		if item[0] == C.SOURCEREAD:
			util.write_var_int(
					((item[1] - 1) << C.OPCODESHIFT) | C.OP_SOURCEREAD,
					out_buf,
				)

		elif item[0] == C.TARGETREAD:
			util.write_var_int(
					((len(item[1]) - 1) << C.OPCODESHIFT) | C.OP_TARGETREAD,
					out_buf,
				)
			out_buf.write(item[1])

		elif item[0] == C.SOURCECOPY:
			util.write_var_int(
					((item[1] - 1) << C.OPCODESHIFT) | C.OP_SOURCECOPY,
					out_buf,
				)
			util.write_var_int(
					(abs(item[2]) << 1) | (item[2] < 0),
					out_buf,
				)

		elif item[0] == C.TARGETCOPY:
			util.write_var_int(
					((item[1] - 1) << C.OPCODESHIFT) | C.OP_TARGETCOPY,
					out_buf,
				)
			util.write_var_int(
					(abs(item[2]) << 1) | (item[2] < 0),
					out_buf,
				)

		elif item[0] == C.SOURCECRC32:
			_, value = item
			out_buf.write(pack("I", value))

		elif item[0] == C.TARGETCRC32:
			_, value = item
			out_buf.write(pack("I", value))

		else:
			raise CorruptFile("Unknown event {0!r}".format(item[0]))

	# Lastly, write out the patch CRC32.
	out_buf.write(pack("I", out_buf.crc32))


def read_blip_asm(in_buf):
	"""
	Yields Blip patch instructions from the Blip patch in in_buf.

	in_buf should implement io.IOBase, opened in 'rt' mode.
	"""
	# header
	magic = in_buf.readline()

	if magic != C.BLIPASM_MAGIC:
		raise CorruptFile("Blip asm should have magic set to {expected!r}, "
				"not {actual!r}".format(expected=C.BLIPASM_MAGIC, actual=magic)
			)

	label, sourcesize = in_buf.readline().split(":")
	_expect_label(C.SOURCESIZE, label)
	sourcesize = int(sourcesize)

	label, targetsize = in_buf.readline().split(":")
	_expect_label(C.TARGETSIZE, label)
	targetsize = int(targetsize)

	label, _ = in_buf.readline().split(":")
	_expect_label(C.METADATA, label)
	metadata = _read_multiline_text(in_buf)

	yield (C.BLIP_MAGIC, sourcesize, targetsize, metadata)

	targetoffset = 0
	while targetoffset < targetsize:
		label, value = in_buf.readline().split(":")
		if label == C.SOURCEREAD:
			length = int(value)
			yield (label, length)
			targetoffset += length

		elif label == C.TARGETREAD:
			data = _read_multiline_text(in_buf)
			data = NON_HEX_DIGIT_RE.sub("", data)
			data = a2b_hex(data)
			yield (label, data)
			targetoffset += len(data)

		elif label in (C.SOURCECOPY, C.TARGETCOPY):
			length, offset = [int(x) for x in value.split()]
			yield (label, length, offset)
			targetoffset += length

		else:
			raise CorruptFile("Unknown label: {label!r}".format(label=label))

	label, sourcecrc32 = in_buf.readline().split(":")
	_expect_label(C.SOURCECRC32, label)
	yield (C.SOURCECRC32, int(sourcecrc32, 16))

	label, targetcrc32 = in_buf.readline().split(":")
	_expect_label(C.TARGETCRC32, label)
	yield (C.TARGETCRC32, int(targetcrc32, 16))


def write_blip_asm(iterable, out_buf):
	"""
	Encodes Blip patch instructions into Blip assembler in out_buf.

	iterable should yield a sequence of Blip patch instructions.

	out_buf should implement io.IOBase, opened in 'wt' mode.
	"""
	# Make sure we have a sensible stream to write.
	iterable = check_stream(iterable)

	# header
	(magic, sourcesize, targetsize, metadata) = next(iterable)

	out_buf.write(C.BLIPASM_MAGIC)
	out_buf.write("{0}: {1:d}\n".format(C.SOURCESIZE, sourcesize))
	out_buf.write("{0}: {1:d}\n".format(C.TARGETSIZE, targetsize))

	# metadata
	out_buf.write("metadata:\n")
	lines = metadata.split("\n")
	if lines[-1] == "":
		lines.pop(-1)
	for line in lines:
		# Because we use a line containing only "." as the delimiter, we
		# need to escape all the lines beginning with dots.
		if line.startswith("."):
			out_buf.write(".")
		out_buf.write(line)
		out_buf.write("\n")

	out_buf.write(".\n")

	for item in iterable:
		if item[0] == C.SOURCEREAD:
			out_buf.write("{0}: {1}\n".format(*item))

		elif item[0] == C.TARGETREAD:
			out_buf.write("{0}:\n".format(item[0]))
			data = item[1]
			while len(data) > 40:
				head, data = data[:40], data[40:]
				out_buf.write(b2a_hex(head).decode('ascii'))
				out_buf.write("\n")
			out_buf.write(b2a_hex(data).decode('ascii'))
			out_buf.write("\n.\n")

		elif item[0] == C.SOURCECOPY:
			out_buf.write("{0}: {1} {2:+d}\n".format(*item))

		elif item[0] == C.TARGETCOPY:
			out_buf.write("{0}: {1} {2:+d}\n".format(*item))

		elif item[0] == C.SOURCECRC32:
			out_buf.write("{0}: {1:08X}\n".format(*item))

		elif item[0] == C.TARGETCRC32:
			out_buf.write("{0}: {1:08X}\n".format(*item))

		else:
			raise CorruptFile("Unknown label: {label!r}".format(label=item[0]))

