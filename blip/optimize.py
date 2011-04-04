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

def optimize(iterable):
	"""
	Yields a simplified sequence of patch operations from iterable.
	"""
	iterable = check_stream(iterable)

	header = next(iterable)
	yield header

	lastItem = next(iterable)

	for item in iterable:

		# FIXME: Another idea for optimizing: if we keep track of
		# targetWriteOffset and sourceRelativeOffset in here, we convert
		# SourceCopy operations with an appropriate offset into SourceRead
		# operations, which should shave off a few bytes.

		if lastItem[0] == C.SOURCEREAD and item[0] == C.SOURCEREAD:
			# We can merge consecutive SourceRead operations.
			lastItem = (C.SOURCEREAD, lastItem[1] + item[1])
			continue

		elif lastItem[0] == C.TARGETREAD and item[0] == C.TARGETREAD:
			# We can merge consecutive TargetRead operations.
			lastItem = (C.TARGETREAD, lastItem[1] + item[1])
			continue

		elif (lastItem[0] == C.SOURCECOPY and item[0] == C.SOURCECOPY and
				item[2] == 0):
			# We can merge consecutive SourceCopy operations, as long as the
			# following ones have a relative offset of 0 from the end of the
			# previous one.
			lastItem = (C.SOURCECOPY, lastItem[1] + item[1], lastItem[2])
			continue

		elif (lastItem[0] == C.TARGETCOPY and item[0] == C.TARGETCOPY and
				item[2] == 0):
			# We can merge consecutive TargetCopy operations, as long as the
			# following ones have a relative offset of 0 from the end of the
			# previous one.
			lastItem = (C.TARGETCOPY, lastItem[1] + item[1], lastItem[2])
			continue

		yield lastItem
		lastItem = item

	yield lastItem
