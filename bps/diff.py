# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

"""
Tools for creating BPS patches.

For more information about the basic algorithm used here, see the article
"Intro to Delta Encoding":

	https://gitorious.org/python-blip/pages/IntroToDeltaEncoding

"""
from zlib import crc32
from bps import operations as ops
from bps.util import BlockMap

def iter_blocks(data, blocksize):
	offset = 0

	while offset < len(data):
		block = data[offset:offset+blocksize]

		yield (block, offset)
		offset += len(block)


def iter_candidate_ops(blocksrc, offsetlist, target, targetoffset, op):
	"""
	Yield operations that encode the block at targetoffset in the target.
	"""
	# Find all the offsets in blocksrc where the given block occurs.
	for sourceoffset in offsetlist:
		# Find how many bytes at sourceoffset match the target at targetoffset.
		bytespan = 0
		while blocksrc[sourceoffset+bytespan] == target[targetoffset+bytespan]:
			bytespan += 1

			if sourceoffset + bytespan >= len(blocksrc): break
			if targetoffset + bytespan >= len(target): break

		if op is ops.SourceCopy and sourceoffset == targetoffset:
			yield [ops.SourceRead(bytespan)]
		else:
			yield [op(bytespan, sourceoffset)]


def op_efficiency(oplist, lastSourceCopyOffset, lastTargetCopyOffset):
	total_bytespan = 0
	total_encoding_size = 0

	for op in oplist:
		total_bytespan += op.bytespan
		total_encoding_size += len(
				op.encode(lastSourceCopyOffset, lastTargetCopyOffset)
			)

	return total_bytespan / total_encoding_size


def diff_bytearrays(source, target, metadata=""):
	"""
	Yield a sequence of patch operations that transform source to target.
	"""
	# Smaller block-sizes make for more efficient diffs, but a larger number of
	# blocks uses more memory. Since we need to keep the block map for the
	# source and target in memory at the same time, calculate a block-size that
	# will give us about a 64-byte block on a 32MB file (since I know from
	# experience that fits in my RAM).
	blocksize = (len(source) + len(target)) // 1000000 + 1

	yield ops.Header(len(source), len(target), metadata)

	# We assume the entire source file will be available when applying this
	# patch, so load the entire thing into the block map.
	sourcemap = BlockMap()
	for block, offset in iter_blocks(source, blocksize):
		sourcemap.add_block(block, offset)

	# Points at the part of the target buffer we're trying to encode.
	targetWriteOffset = 0

	# Points at the byte after the last byte written by the most recent
	# SourceCopy operation.
	lastSourceCopyOffset = 0

	# Points at the byte after the last byte written by the most recent
	# TargetCopy operation.
	lastTargetCopyOffset = 0

	# Keep track of blocks seen in the part of the target buffer before
	# targetWriteOffset. Because targetWriteOffset does not always advance by
	# an even multiple of the blocksize, there can be some lag between when
	# targetWriteOffset moves past a particular byte, and when that byte's
	# block is added to targetmap.
	targetmap = BlockMap()
	targetblocks = iter_blocks(target, blocksize)

	# Points to the byte just beyond the most recent block added to targetmap;
	# the difference between this and targetWriteOffset measures the 'some lag'
	# described above.
	nextTargetBlockOffset = 0

	while targetWriteOffset < len(target):
		block = target[targetWriteOffset:targetWriteOffset+blocksize]

		candidates = []

		# Any matching blocks anywhere in the source buffer are candidates.
		candidates.extend(iter_candidate_ops(
				source, sourcemap.get(block, []),
				target, targetWriteOffset,
				ops.SourceCopy)
			)

		# Any matching blocks in the target buffer that we've added to the
		# targetmap so far are candidates.
		candidates.extend(iter_candidate_ops(
				target, targetmap.get(block, []),
				target, targetWriteOffset,
				ops.TargetCopy)
			)

		# No matter what's in the source and target maps, spitting out one byte
		# and moving on is always an option.
		candidates.append(
				[ops.TargetRead(target[targetWriteOffset:targetWriteOffset+1])]
			)

		# Find the candidate that represents the largest span of data
		candidates.sort(key=lambda x: op_efficiency(x, lastSourceCopyOffset,
			lastTargetCopyOffset))
		oplist = candidates[-1]

		for op in oplist:
			yield op

			if isinstance(op, ops.TargetCopy):
				lastTargetCopyOffset = op.offset + op.bytespan
			if isinstance(op, ops.SourceCopy):
				lastSourceCopyOffset = op.offset + op.bytespan

			targetWriteOffset += op.bytespan

		# If it's been more than BLOCKSIZE bytes since we added a block to
		# targetmap, process the backlog.
		while (targetWriteOffset - nextTargetBlockOffset) >= blocksize:
			newblock, offset = next(targetblocks)
			targetmap.add_block(newblock, offset)
			nextTargetBlockOffset = offset + len(newblock)

	yield ops.SourceCRC32(crc32(source))
	yield ops.TargetCRC32(crc32(target))
