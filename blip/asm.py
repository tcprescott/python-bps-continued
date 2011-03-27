"""
Tools for creating human-readable versions of Blip patch files.
"""
import io
from struct import pack, unpack
from blip import util

def disassemble(in_buf, out_buf):
	"""
	Disassembles the Blip patch in in_buf, writing the result to out_buf.
	"""
	# header
	magic = in_buf.read(4)
	assert magic == b'blip'
	out_buf.write("blipasm\n")

	# source size
	sourcesize = util.read_var_int(in_buf)
	out_buf.write("sourcesize: {0:d}\n".format(sourcesize))

	# target size
	targetsize = util.read_var_int(in_buf)
	out_buf.write("targetsize: {0:d}\n".format(targetsize))

	# metadata
	metadatasize = util.read_var_int(in_buf)
	metadata = in_buf.read(metadatasize).decode('utf-8')
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

	# FIXME: We should do a thing here that counts through patch hunks.
	
	# source crc32
	sourcecrc32 = unpack("I", in_buf.read(4))[0]
	out_buf.write("sourcecrc32: {0:08X}\n".format(sourcecrc32))

	# target crc32
	targetcrc32 = unpack("I", in_buf.read(4))[0]
	out_buf.write("targetcrc32: {0:08X}\n".format(targetcrc32))


def assemble(in_buf, out_buf):
	"""
	Assembles the description in in_buf to a Blip patch in out_buf.
	"""
	# Wrap the output buffer with our CRC32-tracking wrapper.
	out_buf = util.CRCIOWrapper(out_buf)

	# header
	magic = in_buf.readline()
	assert magic == "blipasm\n"
	out_buf.write(b'blip')

	# source size
	label, value = in_buf.readline().split(":")
	assert label == "sourcesize"
	util.write_var_int(int(value), out_buf)

	# target size
	label, value = in_buf.readline().split(":")
	assert label == "targetsize"
	util.write_var_int(int(value), out_buf)

	# metadata
	label = in_buf.readline()
	assert label == "metadata:\n"
	metadata = []
	while True:
		line = in_buf.readline()
		if line == ".\n":
			break
		if line.startswith("."): line = line[1:]
		metadata.append(line)
	metadata = "".join(metadata).encode("utf-8")
	util.write_var_int(len(metadata), out_buf)
	out_buf.write(metadata)

	# FIXME: Handle patch hunks here.
	
	# source crc32
	label, value = in_buf.readline().split(":")
	assert label == "sourcecrc32"
	out_buf.write(pack("I", int(value, 16)))

	# target crc32
	label, value = in_buf.readline().split(":")
	assert label == "targetcrc32"
	out_buf.write(pack("I", int(value, 16)))

	# patch crc32
	out_buf.write(pack("I", out_buf.crc32))
