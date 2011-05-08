# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

"""
Tools for optimizing blip patches.
"""
from io import BytesIO
from blip import constants as C
from blip.validate import check_stream
from blip.util import op_size

# It's semantically correct to concatentate two or more TargetRead operations
# by concatenating their payloads, but repeated string concatenation can be
# hideously inefficient in Python. Therefore, for the duration of this module,
# we define a new operation type, "ElasticTargetRead", that is semantically
# identical to TargetRead, but stores its payload in a BytesIO object rather
# than in a raw bytes object.
ELASTIC_TARGETREAD = "ElasticTargetRead"

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
			# We can merge consecutive TargetRead operations. For efficiency,
			# we'll merge them into an ElasticTargetRead operation.
			buf = BytesIO()
			buf.write(lastItem[1])
			buf.write(item[1])
			lastItem = (ELASTIC_TARGETREAD, buf)
			continue

		elif lastItem[0] == ELASTIC_TARGETREAD and item[0] == C.TARGETREAD:
			# Another item to add to the growing TargetRead.
			lastItem[1].write(item[1])
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
			# A SourceRead is just a SourceCopy that implicitly has its read
			# off set set to targetWriteOffset.
			lastItem = (C.SOURCEREAD, lastItem[1])

		if lastItem[0] == ELASTIC_TARGETREAD:
			# If we've come to the end of the chain of TargetRead operations,
			# merge our buffer back into a single TargetRead operation.
			lastItem = (C.TARGETREAD, lastItem[1].getvalue())

		yield lastItem

		if lastItem[0] in {C.SOURCEREAD, C.TARGETREAD, C.SOURCECOPY,
				C.TARGETCOPY}:
			targetWriteOffset += op_size(lastItem)

		lastItem = item

	if lastItem[0] == ELASTIC_TARGETREAD:
		# If we've come to the end of the chain of TargetRead operations,
		# merge our buffer back into a single TargetRead operation.
		lastItem = (C.TARGETREAD, lastItem[1].getvalue())

	yield lastItem
