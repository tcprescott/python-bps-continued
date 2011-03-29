"""
Tools for reading blip patches.
"""
from struct import pack, unpack
from blip import util
from blip import constants as C

class CorruptFile(ValueError):
	pass

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
		raise CorruptFile("File magic should be {expected:r}, got "
				"{actual:r}".format(expected=C.BLIP_MAGIC, actual=magic))

	sourcesize = util.read_var_int(in_buf)
	targetsize = util.read_var_int(in_buf)
	metadatasize = util.read_var_int(in_buf)
	metadata = in_buf.read(metadatasize).decode('utf-8')

	yield (magic, sourcesize, targetsize, metadata)

	# FIXME: We should do a thing here that counts through patch hunks.

	# footer
	yield (C.SOURCECRC32, unpack("I", in_buf.read(4))[0])
	yield (C.TARGETCRC32, unpack("I", in_buf.read(4))[0])

	# Check the patch's CRC32.
	actual = in_buf.crc32
	expected = unpack("I", in_buf.read(4))[0]

	if expected != actual:
		raise CorruptFile("Patch claims its CRC32 is {expected:r}, but "
				"it's really {actual:08X}".format(
					expected=expected, actual=actual)
			)

def write_blip(iterable, out_buf):
	"""
	Encodes Blip patch instructions from the iterable into a patch in out_buf.

	iterable should yield a sequence of Blip patch instructions.

	out_buf should implement io.IOBase, opened in 'wb' mode.
	"""
	# We really want an iterable.
	iterable = iter(iterable)

	# Keep track of the patch data's CRC32, so we can write it out at the end.
	out_buf = util.CRCIOWrapper(out_buf)

	# header
	(magic, sourcesize, targetsize, metadata) = next(iterable)

	if magic != C.BLIP_MAGIC:
		raise CorruptFile("File magic should be {expected!r}, got "
				"{actual!r}".format(expected=C.BLIP_MAGIC, actual=magic))

	out_buf.write(magic)
	util.write_var_int(sourcesize, out_buf)
	util.write_var_int(targetsize, out_buf)
	metadata = metadata.encode('utf-8')
	util.write_var_int(len(metadata), out_buf)
	out_buf.write(metadata)

	allowedEvents = { C.SOURCECRC32 }
	for item in iterable:
		if item[0] not in allowedEvents:
			raise CorruptFile("Event should be one of {allowed!r}, not "
					"{actual!r}".format(allowed=allowedEvents, actual=item[0]))

		# FIXME: We should do a thing here that handles patch hunks.

		if item[0] == C.SOURCECRC32:
			_, value = item
			out_buf.write(pack("I", value))
			allowedEvents = { C.TARGETCRC32 }
		elif item[0] == C.TARGETCRC32:
			_, value = item
			out_buf.write(pack("I", value))
			allowedEvents = set()

	if len(allowedEvents) != 0:
		raise CorruptFile("Event stream was truncated. Expected one of "
				"{allowed!r} next.".format(allowed=allowedEvents))

	# Lastly, write out the patch CRC32.
	out_buf.write(pack("I", out_buf.crc32))
