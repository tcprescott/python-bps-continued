# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

"""
Tools for optimizing blip patches.
"""
from blip import constants as C
from blip.validate import check_stream

def _itemlen(item):
	"""
	Returns the number of bytes written by a patch operation.
	"""
	if item[0] in {C.SOURCEREAD, C.SOURCECOPY, C.TARGETCOPY}:
		return item[1]
	elif item[0] == C.TARGETREAD:
		return len(item[1])
	else:
		return None

def optimize(iterable):
	"""
	Yields a simplified sequence of patch operations from iterable.
	"""
	iterable = check_stream(iterable)

	header = next(iterable)
	yield header

	lastItem = next(iterable)

	if lastItem[0] == C.SOURCECOPY and lastItem[2] == 0:
		# SourceCopy is copying from the start of the file, so it might as well
		# be a SourceRead.
		lastItem = (C.SOURCEREAD, lastItem[1])

	targetWriteOffset = 0
	for item in iterable:

		if lastItem[0] == C.SOURCEREAD and item[0] == C.SOURCEREAD:
			# We can merge consecutive SourceRead operations.
			lastItem = (C.SOURCEREAD, lastItem[1] + item[1])
			continue

		elif lastItem[0] == C.TARGETREAD and item[0] == C.TARGETREAD:
			# We can merge consecutive TargetRead operations.
			lastItem = (C.TARGETREAD, lastItem[1] + item[1])
			continue

		elif (lastItem[0] == C.SOURCECOPY and item[0] == C.SOURCECOPY and
				lastItem[1] + lastItem[2] == item[2]):
			# We can merge consecutive SourceCopy operations, as long as the
			# following ones have a relative offset of 0 from the end of the
			# previous one.
			lastItem = (C.SOURCECOPY, lastItem[1] + item[1], lastItem[2])
			continue

		elif (lastItem[0] == C.TARGETCOPY and item[0] == C.TARGETCOPY and
				lastItem[1] + lastItem[2] == item[2]):
			# We can merge consecutive TargetCopy operations, as long as the
			# following ones have a relative offset of 0 from the end of the
			# previous one.
			lastItem = (C.TARGETCOPY, lastItem[1] + item[1], lastItem[2])
			continue

		if lastItem[0] == C.SOURCECOPY and lastItem[2] == targetWriteOffset:
			lastItem = (C.SOURCEREAD, lastItem[1])

		yield lastItem

		if lastItem[0] in {C.SOURCEREAD, C.TARGETREAD, C.SOURCECOPY,
				C.TARGETCOPY}:
			targetWriteOffset += _itemlen(lastItem)

		lastItem = item

	yield lastItem
