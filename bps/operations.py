# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

"""
Classes representing patch operations.
"""
from struct import pack
from bps import util
from bps import constants as C


def _classname(obj):
	return "{0.__module__}.{0.__name__}".format(type(obj))


class BaseOperation:

	# Unless otherwise configured, an operation affects no bytes.
	bytespan = 0

	def encode(self, sourceRelativeOffset, targetRelativeOffset):
		"""
		Returns a bytestring representing this operation.

		sourceRelativeOffset is used when encoding SourceCopy operations,
		targetRelativeOffset is used when encoding TargetCopy operations.
		"""
		raise NotImplementedError()

	def extend(self, other):
		"""
		Concatenate the other operation with this one, if possible.

		Raises TypeError if the other operation is of an incompatible type, or
		ValueError if the other operation isn't contiguous with this one.
		"""


class Header(BaseOperation):

	__slots__ = [
			'sourceSize',
			'targetSize',
			'metadata',
		]

	def __init__(self, sourceSize, targetSize, metadata=""):
		assert isinstance(sourceSize, int)
		assert isinstance(targetSize, int)
		assert sourceSize >= 0
		assert targetSize >= 0
		assert isinstance(metadata, str)

		self.sourceSize = sourceSize
		self.targetSize = targetSize
		self.metadata = metadata

	def __repr__(self):
		return (
				"<{0} "
				"sourceSize={1.sourceSize} "
				"targetSize={1.targetSize}>".format(_classname(self), self)
			)

	def __eq__(self, other):
		if not isinstance(other, type(self)): return False

		if self.sourceSize != other.sourceSize: return False
		if self.targetSize != other.targetSize: return False
		if self.metadata   != other.metadata:   return False

		return True

	def extend(self, other):
		raise TypeError(
				"Cannot extend a header operation with {0!r}".format(other)
			)

	def encode(self, ignored, ignored2):
		res = [C.BPS_MAGIC]
		res.append(util.encode_var_int(self.sourceSize))
		res.append(util.encode_var_int(self.targetSize))

		metadata = self.metadata.encode('utf-8')
		res.append(util.encode_var_int(len(metadata)))
		res.append(metadata)

		return b''.join(res)


class SourceRead(BaseOperation):

	__slots__ = ['bytespan']

	def __init__(self, bytespan):
		assert isinstance(bytespan, int)
		assert bytespan > 0

		self.bytespan = bytespan

	def __repr__(self):
		return "<{0} bytespan={1.bytespan}>".format(
				_classname(self), self)

	def __eq__(self, other):
		if not isinstance(other, type(self)): return False

		if self.bytespan != other.bytespan: return False

		return True

	def extend(self, other):
		if not isinstance(other, type(self)):
			raise TypeError(
					"Cannot extend a SourceRead with {0!r}".format(other)
				)
		self.bytespan += other.bytespan

	def encode(self, ignored, ignored2):
		return util.encode_var_int(
				(self.bytespan - 1) << C.OPCODESHIFT | C.OP_SOURCEREAD
			)


class TargetRead(BaseOperation):

	__slots__ = ['_payload']

	def __init__(self, payload):
		assert isinstance(payload, bytes)
		assert len(payload) > 0

		self._payload = [payload]

	def __repr__(self):
		return "<{0} bytespan={1.bytespan}>".format(
				_classname(self), self
			)

	def __eq__(self, other):
		if not isinstance(other, type(self)): return False

		if self.payload != other.payload: return False

		return True

	@property
	def payload(self):
		# If we have multiple byte-chunks in the payload, join them together
		# then store the result so we don't have to do that (potentially
		# expensive) operation again.
		if len(self._payload) > 1:
			self._payload = [b''.join(self._payload)]
		return self._payload[0]

	@property
	def bytespan(self):
		return len(self.payload)

	def extend(self, other):
		if not isinstance(other, type(self)):
			raise TypeError(
					"Cannot extend a TargetRead with {0!r}".format(other)
				)
		self._payload.append(other.payload)

	def encode(self, ignored, ignored2):
		payload = self.payload
		return b''.join([
				util.encode_var_int(
					(len(payload) - 1) << C.OPCODESHIFT | C.OP_TARGETREAD
				),
				payload,
			])


class _BaseCopy(BaseOperation):

	__slots__ = [
			'bytespan',
			'offset',
		]

	def __init__(self, bytespan, offset):
		assert isinstance(bytespan, int)
		assert bytespan > 0
		assert isinstance(offset, int)
		assert offset >= 0

		self.bytespan = bytespan
		self.offset = offset

	def __repr__(self):
		return "<{0} bytespan={1.bytespan} offset={1.offset}>".format(
				_classname(self), self
			)

	def __eq__(self, other):
		if not isinstance(other, type(self)): return False

		if self.bytespan != other.bytespan: return False
		if self.offset   != other.offset:   return False

		return True

	def extend(self, other):
		if not isinstance(other, type(self)):
			raise TypeError(
					"Cannot extend a {0} with {1!r}".format(
						type(self).__name__, other,
					)
				)
		if other.offset != self.offset + self.bytespan:
			raise ValueError(
					"Cannot extend {0!r} with non-contiguous op {1!r}".format(
						self, other,
					)
				)

		self.bytespan += other.bytespan


class SourceCopy(_BaseCopy):

	def encode(self, sourceRelativeOffset, ignored):
		relOffset = self.offset - sourceRelativeOffset

		return b''.join([
				util.encode_var_int(
					(self.bytespan - 1) << C.OPCODESHIFT | C.OP_SOURCECOPY
				),
				util.encode_var_int(
					(abs(relOffset) << 1) | (relOffset < 0)
				),
			])


class TargetCopy(_BaseCopy):

	def encode(self, ignored, targetRelativeOffset):
		relOffset = self.offset - targetRelativeOffset

		return b''.join([
				util.encode_var_int(
					(self.bytespan - 1) << C.OPCODESHIFT | C.OP_TARGETCOPY
				),
				util.encode_var_int(
					(abs(relOffset) << 1) | (relOffset < 0)
				),
			])


class _BaseCRC32(BaseOperation):

	__slots__ = [
			'value',
		]

	def __init__(self, value):
		assert isinstance(value, int)
		assert value >= 0
		assert value < 2**32

		self.value = value

	def __repr__(self):
		return "<{0} value=0x{1.value:08X}>".format(
				_classname(self), self
			)

	def __eq__(self, other):
		if not isinstance(other, type(self)): return False

		if self.value != other.value: return False

		return True

	def extend(self, other):
		raise TypeError(
				"Cannot extend {0!r} with {1!r}".format(self, other)
			)

	def encode(self, ignored, ignored2):
		return pack("<I", self.value)


class SourceCRC32(_BaseCRC32):
	pass


class TargetCRC32(_BaseCRC32):
	pass
