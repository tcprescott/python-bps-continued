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
from blip import operations as ops


class BlockMap(dict):

	def add_block(self, block, offset):
		offsetlist = self.setdefault(block, [])
		bisect.insort(offsetlist, offset)

	def nearest_instance(self, block, offset):
		offsetlist = self[block]
		index = bisect.bisect(offsetlist, offset)
		index = min(index, len(offsetlist)-1)
		return offsetlist[index]


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
	yield ops.Header(len(source), len(target), metadata)

	sourcemap = BlockMap()
	for block, offset in iter_blocks(source):
		sourcemap.add_block(block, offset)

	targetWriteOffset = 0
	lastSourceCopyOffset = 0
	lastTargetCopyOffset = 0

	targetmap = BlockMap()
	for block, offset in iter_blocks(target):
		if block in sourcemap and offset in sourcemap[block]:
			yield ops.SourceRead(len(block))

		elif block in targetmap:
			# We prefer blocks in targetmap to blocks in sourcemap, because
			# blocks in targetmap have more potential for RLE.

			lastoffset = targetmap[block][-1]
			if lastoffset == (targetWriteOffset - len(block)):
				# If the most recent instance of this block was the very last
				# thing written, use it. That means the two TargetCopy
				# operations can be combined.
				srcoffset = lastoffset
			else:
				# Otherwise, pick the instance closest to targetRelativeOffset
				# so that the operation will have the smallest encoding.
				srcoffset = targetmap.nearest_instance(block,
						lastTargetCopyOffset)

			yield ops.TargetCopy(len(block), srcoffset)

			lastTargetCopyOffset = srcoffset + len(block)

		elif block in sourcemap:
			srcoffset = sourcemap.nearest_instance(block, lastSourceCopyOffset)
			yield ops.SourceCopy(len(block), srcoffset)

			lastSourceCopyOffset = srcoffset + len(block)

		else:
			yield ops.TargetRead(block)

		targetWriteOffset += len(block)
		targetmap.add_block(block, offset)

	yield ops.SourceCRC32(crc32(source))
	yield ops.TargetCRC32(crc32(target))
