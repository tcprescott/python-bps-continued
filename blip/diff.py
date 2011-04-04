# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

"""
Tools for creating Blip patches.
"""
import sys
import bisect
from zlib import crc32
from blip import constants as C


def iter_blocks(data, blocksize=64, delim=b'\n'):
	offset = 0

	while offset < len(data):
		next_delim = data.find(delim, offset)

		if next_delim == -1:
			endpoint = len(data)
		else:
			endpoint = next_delim + 1

		while offset < endpoint:
			if (endpoint-offset) > blocksize:
				block = data[offset:offset+blocksize]
			else:
				block = data[offset:endpoint]

			yield (block, offset)
			offset += len(block)


def diff_bytearrays(source, target, metadata=""):
	"""
	Yield a sequence of patch operations that transform source to target.
	"""
	yield (C.BLIP_MAGIC, len(source), len(target), metadata)

	sourcemap = {}
	for block, offset in iter_blocks(source):
		offsetlist = sourcemap.setdefault(block, [])
		bisect.insort(offsetlist, offset)

	targetWriteOffset = 0
	sourceRelativeOffset = 0
	targetRelativeOffset = 0

	targetmap = {}
	for block, offset in iter_blocks(target):
		if block in sourcemap and offset in sourcemap[block]:
			yield (C.SOURCEREAD, len(block))

		elif block in targetmap:
			# We prefer blocks in targetmap to blocks in sourcemap, because
			# blocks in targetmap have more potential for RLE.
			offsetlist = targetmap[block]

			if offsetlist[-1] == (targetWriteOffset - len(block)):
				# If the most recent instance of this block was the very last
				# thing written, use it. That means the two TargetCopy
				# operations can be combined.
				index = -1
			else:
				# Otherwise, pick the instance closest to targetRelativeOffset
				# so that the operation will have the smallest encoding.
				index = bisect.bisect(offsetlist, sourceRelativeOffset)
				index = min(index, len(offsetlist)-1)

			yield (C.TARGETCOPY, len(block),
					(offsetlist[index] - targetRelativeOffset))

			targetRelativeOffset = offsetlist[index] + len(block)

		elif block in sourcemap:
			offsetlist = sourcemap[block]

			index = bisect.bisect(offsetlist, sourceRelativeOffset)
			index = min(index, len(offsetlist)-1)

			yield (C.SOURCECOPY, len(block),
					(offsetlist[index] - sourceRelativeOffset))

			sourceRelativeOffset = offsetlist[index] + len(block)

		else:
			yield (C.TARGETREAD, block)

		targetWriteOffset += len(block)

		offsetlist = targetmap.setdefault(block, [])
		bisect.insort(offsetlist, offset)

	yield (C.SOURCECRC32, crc32(source))
	yield (C.TARGETCRC32, crc32(target))
