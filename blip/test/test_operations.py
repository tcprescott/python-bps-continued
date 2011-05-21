#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

import sys
import unittest
from blip import operations as ops

class TestHeader(unittest.TestCase):

	@unittest.skipIf(sys.flags.optimize, 'Optimizing disables assertions')
	def test_validation(self):
		"""
		The header op checks its parameters.
		"""
		self.assertRaises(AssertionError, ops.Header, '0', 0, "")
		self.assertRaises(AssertionError, ops.Header, 0, '0', "")
		self.assertRaises(AssertionError, ops.Header, -1, 0, "")
		self.assertRaises(AssertionError, ops.Header, 0, -1, "")
		self.assertRaises(AssertionError, ops.Header, 0, 0, b"")

	def test_attributes(self):
		"""
		The header op sets its properties from its parameters.
		"""
		header = ops.Header(1, 2, "3")
		self.assertEqual(header.sourceSize, 1)
		self.assertEqual(header.targetSize, 2)
		self.assertEqual(header.metadata, "3")

	def test_bytespan_zero(self):
		"""
		The header op must report its bytespan as zero.
		"""
		header = ops.Header(1, 2, "3")
		self.assertEqual(header.bytespan, 0)
	
	def test_cannot_extend(self):
		"""
		The header op cannot be extended.
		"""
		header1 = ops.Header(1, 2, "3")
		header2 = ops.Header(4, 5, "6")

		self.assertRaisesRegex(TypeError, "Cannot extend a header",
				header1.extend, header2)

	def test_encode(self):
		"""
		The header op produces the correct byte encoding.
		"""
		header = ops.Header(1, 2, "café")
		self.assertEqual(header.encode(0,0), b'blip\x81\x82\x85caf\xc3\xa9')


class TestSourceRead(unittest.TestCase):

	@unittest.skipIf(sys.flags.optimize, 'Optimizing disables assertions')
	def test_validation(self):
		"""
		The SourceRead op checks its parameters.
		"""
		self.assertRaises(AssertionError, ops.SourceRead, '1')
		self.assertRaises(AssertionError, ops.SourceRead, 0)

	def test_attributes(self):
		"""
		The SourceRead op sets its properties from its parameters.
		"""
		op = ops.SourceRead(5)
		self.assertEqual(op.bytespan, 5)

	def test_extend_with_SourceRead(self):
		"""
		We can extend one SourceRead with another.

		Strictly speaking, of course we can't extend a SourceRead with *any*
		other SourceRead, only if the two are next to each other in the
		operation stream. Since individual SourceRead operations don't store
		that information, we can't check it, so we default to 'yes'.
		"""
		op1 = ops.SourceRead(5)
		op2 = ops.SourceRead(6)
		op1.extend(op2)

		# The extended operation has incorporated the length of its fellow.
		self.assertEqual(op1.bytespan, 11)

		# The second operation is unchanged, and should be discarded.
		self.assertEqual(op2.bytespan, 6)

	def test_cannot_extend_with_others(self):
		"""
		The SourceRead op cannot be extended with other operations.
		"""
		op1 = ops.SourceRead(5)
		op2 = ops.Header(0, 1)

		self.assertRaises(TypeError, op1.extend, op2)

	def test_encode(self):
		"""
		The SourceRead op produces the correct byte encoding.
		"""
		op = ops.SourceRead(5)
		self.assertEqual(op.encode(0, 0), b'\x90')


class TestTargetRead(unittest.TestCase):

	@unittest.skipIf(sys.flags.optimize, 'Optimizing disables assertions')
	def test_validation(self):
		"""
		The TargetRead op checks its parameters.
		"""
		self.assertRaises(AssertionError, ops.TargetRead, b'')
		self.assertRaises(AssertionError, ops.TargetRead, 1)

	def test_attributes(self):
		"""
		The TargetRead op sets its properties from its parameters.
		"""
		op = ops.TargetRead(b'A')
		# The payload is stored in a list so we can efficiently extend it
		# later.
		self.assertEqual(op.payload, b'A')

	def test_bytespan(self):
		"""
		The TargetRead op's bytespan is the length of its payload.
		"""
		self.assertEqual(ops.TargetRead(b'A'  ).bytespan, 1)
		self.assertEqual(ops.TargetRead(b'AAA').bytespan, 3)

	def test_extend_with_TargetRead(self):
		"""
		We can extend one TargetRead with another.
		"""
		op1 = ops.TargetRead(b'A')
		op2 = ops.TargetRead(b'B')

		op1.extend(op2)
		self.assertEqual(op1.payload, b'AB')

	def test_cannot_extend_with_others(self):
		"""
		The TargetRead op cannot be extended with other operations.
		"""
		op1 = ops.TargetRead(b'A')
		op2 = ops.SourceRead(5)

		self.assertRaises(TypeError, op1.extend, op2)

	def test_encode(self):
		"""
		The TargetRead op produces the correct byte encoding.
		"""
		op = ops.TargetRead(b'A')
		self.assertEqual(op.encode(0, 0), b'\x81A')


class CopyOperationTestsMixIn:

	constructor = None

	@unittest.skipIf(sys.flags.optimize, 'Optimizing disables assertions')
	def test_validation(self):
		"""
		This operation checks its parameters.
		"""
		self.assertRaises(AssertionError, self.constructor, "", 0)
		self.assertRaises(AssertionError, self.constructor, 0, 0)
		self.assertRaises(AssertionError, self.constructor, 1, "")
		self.assertRaises(AssertionError, self.constructor, 1, -1)

	def test_attributes(self):
		"""
		This operation sets its properties from its parameters.
		"""
		op = self.constructor(1, 2)
		self.assertEqual(op.bytespan, 1)
		self.assertEqual(op.offset, 2)

	def test_extend_with_contiguous_op(self):
		"""
		We can extend one operation with another if they're contiguous.
		"""
		op1 = self.constructor(2, 3) # Copies [3:5]
		op2 = self.constructor(4, 5) # Copies [5:9]

		op1.extend(op2)

		# Now op1 copies [3:9]
		self.assertEqual(op1.bytespan, 6)
		self.assertEqual(op1.offset, 3)

	def test_cannot_extend_with_distant_op(self):
		"""
		This op cannot be extended by an op that doesn't line up.
		"""
		op1 = self.constructor(2, 3) # Copies [3:5]
		op2 = self.constructor(4, 6) # Copies [6:10]

		self.assertRaises(ValueError, op1.extend, op2)

	def test_cannot_extend_with_different_op(self):
		"""
		This op cannot be extended with an op of a different type.
		"""
		op1 = self.constructor(1, 2)
		op2 = ops.Header(0, 1)

		self.assertRaises(TypeError, op1.extend, op2)


class TestSourceCopy(CopyOperationTestsMixIn, unittest.TestCase):

	constructor = ops.SourceCopy

	def test_encode(self):
		"""
		The SourceCopy op produces the correct byte encoding.
		"""
		# If the 'sourceRelativeOffset' is zero, the recorded offset is just as
		# per normal, shifted up by one to make way for the sign bit.
		op = ops.SourceCopy(1, 2)
		self.assertEqual(op.encode(0, 0), b'\x82\x84')

		# If the 'sourceRelativeOffset' is less than the operation's offset,
		# the recorded offset will be smaller.
		self.assertEqual(op.encode(1, 0), b'\x82\x82')

		# If the 'sourceRelativeOffset' is greater than the operation's offset,
		# the recorded offset will be negative.
		self.assertEqual(op.encode(3, 0), b'\x82\x83')


class TestTargetCopy(CopyOperationTestsMixIn, unittest.TestCase):

	constructor = ops.TargetCopy

	def test_encode(self):
		"""
		The TargetCopy op produces the correct byte encoding.
		"""
		# If the 'targetRelativeOffset' is zero, the recorded offset is just as
		# per normal, shifted up by one to make way for the sign bit.
		op = ops.TargetCopy(1, 2)
		self.assertEqual(op.encode(0, 0), b'\x83\x84')

		# If the 'sourceRelativeOffset' is less than the operation's offset,
		# the recorded offset will be smaller.
		self.assertEqual(op.encode(0, 1), b'\x83\x82')

		# If the 'sourceRelativeOffset' is greater than the operation's offset,
		# the recorded offset will be negative.
		self.assertEqual(op.encode(0, 3), b'\x83\x83')


class CRCOperationTestsMixIn:

	constructor = None

	@unittest.skipIf(sys.flags.optimize, 'Optimizing disables assertions')
	def test_validation(self):
		"""
		This operation checks its parameters.
		"""
		self.assertRaises(AssertionError, self.constructor, "")
		self.assertRaises(AssertionError, self.constructor, -1)
		self.assertRaises(AssertionError, self.constructor, 2**32)
	
	def test_attributes(self):
		"""
		This operations sets its properties from its parameters.
		"""
		op = self.constructor(35)
		self.assertEqual(op.value, 35)

	def test_cannot_extend(self):
		"""
		A CRC operation cannot be extended.
		"""
		op1 = self.constructor(1)
		op2 = self.constructor(2)

		self.assertRaisesRegex(TypeError, "Cannot extend",
				op1.extend, op2)

	def test_encode(self):
		"""
		A CRC operation produces the correct byte encoding.
		"""
		op = self.constructor(0x11223344)
		self.assertEqual(
				op.encode(0,0),
				b'\x44\x33\x22\x11',
			)


class TestSourceCRC32(CRCOperationTestsMixIn, unittest.TestCase):

	constructor = ops.SourceCRC32


class TestTargetCRC32(CRCOperationTestsMixIn, unittest.TestCase):

	constructor = ops.TargetCRC32


if __name__ == "__main__":
	unittest.main()
