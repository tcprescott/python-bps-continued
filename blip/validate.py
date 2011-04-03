"""
Tools for validating Blip patches.
"""
from blip import constants as C


class CorruptFile(ValueError):
	"""
	Raised to indicate that a Blip patch is not valid.
	"""
	pass


def _check_param_count(item, count):
	"""
	Internal function.

	Check that this item has the required parameter count.
	"""
	if len(item) - 1 != count:
		raise CorruptFile("bad hunk: {opcode!r} requires {count} "
				"parameter(s): {item!r}".format(opcode=item[0],
					count=count, item=item))


def _check_length(item):
	"""
	Internal function.

	Check the length parameter of this item.
	"""
	if not isinstance(item[1], int):
		raise CorruptFile("bad hunk: length {length!r} is not a valid "
				"integer: {item!r}".format(length=item[1], item=item))

	if item[1] <= 0:
		raise CorruptFile("bad hunk: length {length!r} must be greater than "
				"zero: {item!r}".format(length=item[1], item=item))


def _check_offset(item):
	"""
	Internal function.

	Check the offset parameter of this item.
	"""
	if not isinstance(item[2], int):
		raise CorruptFile("bad hunk: offset {offset!r} is not a valid "
				"integer: {item!r}".format(offset=item[1], item=item))


def _check_crc32(item, expectedOpcode):
	"""
	Internal function.

	Check the CRC32 parameter of this item.
	"""
	_check_param_count(item, 1)

	if item[0] != expectedOpcode:
		raise CorruptFile("bad hunk: expected {expected}, not opcode "
				"{opcode}: {item}".format(expected=expectedOpcode,
					opcode=item[0], item=item))

	if not isinstance(item[1], int):
		raise CorruptFile("bad crc32: {crc32!r} is not a valid "
				"integer: {item!r}".format(crc32=item[1], item=item))

	if item[1] < 0:
		raise CorruptFile("bad crc32: must be at least zero: "
				"{item!r}".format(crc32=item[1], item=item))

	if item[1] > (2**32 - 1):
		raise CorruptFile("bad crc32: must be less than "
				"2**32: {item!r}".format(crc32=item[1], item=item))


def _check_next(iterable):
	"""
	Internal function.

	Check the iterable does have a next value, and return it.
	"""
	try:
		return next(iterable)
	except StopIteration:
		raise CorruptFile("truncated patch: expected more opcodes after this.")


def check_stream(iterable):
	"""
	Yields items from iterable if they represent a valid Blip patch.

	Raises CorruptFile if any problems are detected.
	"""
	# Make sure we have an iterable.
	iterable = iter(iterable)

	# FIXME: Raise CorruptFile if this raises StopIteration
	header = _check_next(iterable)

	if len(header) != 4:
		raise CorruptFile("bad header: must have exactly 4 items, not "
				"{header!r}".format(header=header))

	if not isinstance(header[0], bytes):
		raise CorruptFile("bad header: magic must be bytes, not "
				"{magic!r}".format(magic=header[0]))

	if header[0] != C.BLIP_MAGIC:
		raise CorruptFile("bad magic: magic must be b'blip', not "
				"{magic!r}".format(magic=header[0]))

	if not isinstance(header[1], int):
		raise CorruptFile("source size is not a valid integer: "
				"{sourcesize!r}".format(sourcesize=header[1]))

	if header[1] < 0:
		raise CorruptFile("source size must be at least zero, not "
				"{sourcesize!r}".format(sourcesize=header[1]))

	if not isinstance(header[2], int):
		raise CorruptFile("target size is not a valid integer: "
				"{targetsize!r}".format(targetsize=header[2]))

	if header[2] < 0:
		raise CorruptFile("target size must be at least zero, not "
				"{targetsize!r}".format(targetsize=header[2]))

	if not isinstance(header[3], str):
		raise CorruptFile("metadata must be a string, not "
				"{metadata!r}".format(metadata=header[3]))

	yield header

	sourceSize           = header[1]
	targetSize           = header[2]
	targetWriteOffset    = 0
	sourceRelativeOffset = 0
	targetRelativeOffset = 0

	while targetWriteOffset < targetSize:
		item = _check_next(iterable)

		if item[0] == C.SOURCEREAD:
			_check_param_count(item, 1)
			_check_length(item)

			# This opcode reads from the source file, from targetWriteOffset to
			# targetWriteOffset+length, so we need to be sure that byte-range
			# exists in the source file as well as the target.
			if targetWriteOffset + item[1] > sourceSize:
				raise CorruptFile("bad hunk: reads past the end of the "
						"source file: {item!r}".format(item=item))

			targetWriteOffset += item[1]

		elif item[0] == C.TARGETREAD:
			_check_param_count(item, 1)

			if not isinstance(item[1], bytes):
				raise CorruptFile("bad hunk: targetread data must be bytes, "
						"not {data!r}: {item!r}".format(data=item[1],
							item=item))

			if len(item[1]) == 0:
				raise CorruptFile("bad hunk: targetread data must not be "
						"empty: {item!r}".format(item=item))

			targetWriteOffset += len(item[1])

		elif item[0] == C.SOURCECOPY:
			_check_param_count(item, 2)
			_check_length(item)
			_check_offset(item)

			# Not allowed to SourceCopy from before the beginning of the source
			# file.
			if sourceRelativeOffset + item[2] < 0:
				raise CorruptFile("bad hunk: reads from before the beginning "
						"of the source file: {item!r}".format(item=item))

			# Not allowed to SourceCopy past the end of the source file.
			if sourceRelativeOffset + item[2] + item[1] > sourceSize:
				raise CorruptFile("bad hunk: reads past the end "
						"of the source file: {item!r}".format(item=item))

			# After each SourceCopy, the sourceRelativeOffset pointer points at
			# the end of the chunk that was copied.
			sourceRelativeOffset += (item[1] + item[2])

			targetWriteOffset += item[1]

		elif item[0] == C.TARGETCOPY:
			_check_param_count(item, 2)
			_check_length(item)
			_check_offset(item)

			# Not allowed to TargetCopy from before the beginning of the target
			# file.
			if targetRelativeOffset + item[2] < 0:
				raise CorruptFile("bad hunk: reads from before the beginning "
						"of the target file: {item!r}".format(item=item))

			# Not allowed to TargetCopy an offset that points past the part
			# we've written.
			if targetRelativeOffset + item[2] >= targetWriteOffset:
				raise CorruptFile("bad hunk: reads past the end "
						"of the written part of the target file: "
						"{item!r}".format(item=item))

			# After each TargetCopy, the targetRelativeOffset pointer points at
			# the end of the chunk that was copied.
			targetRelativeOffset += (item[1] + item[2])

			targetWriteOffset += item[1]

		else:
			raise CorruptFile("bad hunk: unknown opcode {opcode}: "
					"{item!r}".format(opcode=item[0], item=item))

		if targetWriteOffset > targetSize:
			raise CorruptFile("bad hunk: writes past the end of the target: "
					"{item!r}".format(item=item))

		yield item

	sourcecrc32 = _check_next(iterable)
	_check_crc32(sourcecrc32, C.SOURCECRC32)
	yield sourcecrc32

	targetcrc32 = _check_next(iterable)
	_check_crc32(targetcrc32, C.TARGETCRC32)
	yield targetcrc32

	# Check that the iterable is now empty.
	try:
		garbage = next(iterable)
		raise CorruptFile("trailing garbage in stream: {garbage!r}".format(
				garbage=garbage))
	except StopIteration:
		pass


