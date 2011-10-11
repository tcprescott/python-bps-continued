#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

import sys
import unittest
from bps import operations as ops

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
		self.assertEqual(header.encode(0,0), b'BPS1\x81\x82\x85caf\xc3\xa9')

	def test_efficiency(self):
		"""
		Since bytespan is zero, headers have efficiency 0.
		"""
		header = ops.Header(1, 2)
		self.assertEqual(header.efficiency(0,0), 0)

	def test_encoded_size(self):
		"""
		A header's encoded size depends on the size of its parameters.
		"""
		# If each lengths fits in a single byte and there's no metadata, the
		# encoded size should be 7 bytes
		h1 = ops.Header(1, 2, "")
		self.assertEqual(h1.encoded_size(0,0), 4 + 1 + 1 + 1 + 0)

		# If one length takes more than a single byte, the size should be
		# 8 bytes.
		h2 = ops.Header(128, 2, "")
		self.assertEqual(h2.encoded_size(0,0), 4 + 2 + 1 + 1 + 0)
		h3 = ops.Header(1, 128, "")
		self.assertEqual(h3.encoded_size(0,0), 4 + 1 + 2 + 1 + 0)

		# If there's metadata whose length fits in a single byte, the size
		# increases by the length of the metadata.
		h4 = ops.Header(1, 2, "A" * 5)
		self.assertEqual(h4.encoded_size(0,0), 4 + 1 + 1 + 1 + 5)

		# Header size does not depend on last copy offsets.
		self.assertEqual(h4.encoded_size(1000,1000), 4 + 1 + 1 + 1 + 5)

	def test_equality(self):
		"""
		Header ops are equal if their properties are equal.
		"""
		op1 = ops.Header(1, 1, "1")
		op2 = ops.Header(1, 1, "1")

		self.assertEqual(op1, op2)

		op3 = ops.Header(2, 1, "1")
		self.assertNotEqual(op1, op3)

		op4 = ops.Header(1, 2, "1")
		self.assertNotEqual(op1, op4)

		op5 = ops.Header(1, 1, "2")
		self.assertNotEqual(op1, op5)

		self.assertNotEqual(op1, (1, 1, "1"))

	def test_no_marker(self):
		"""
		Headers have no marker string.
		"""
		op = ops.Header(1, 1, "1")
		self.assertEqual(op.marker, None)

	def test_cannot_shrink(self):
		"""
		The header op cannot be shrunk.
		"""
		op = ops.Header(1, 2, "3")

		self.assertRaisesRegex(TypeError, "Cannot shrink a header",
				op.shrink, 5)


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

	def test_efficiency(self):
		"""
		The SourceRead op's efficiency only depends on its length.
		"""
		op = ops.SourceRead(1)
		self.assertAlmostEqual(op.efficiency(   0,    0), 1.0, delta=0.01)
		self.assertAlmostEqual(op.efficiency(1000, 1000), 1.0, delta=0.01)

		op = ops.SourceRead(2)
		self.assertAlmostEqual(op.efficiency(   0,    0), 2.0, delta=0.01)
		self.assertAlmostEqual(op.efficiency(1000, 1000), 2.0, delta=0.01)

	def test_encoded_size(self):
		"""
		The SourceRead op's encoded size depends only on its length.
		"""
		# A SourceRead with a small length fits in 1 byte.
		op = ops.SourceRead(32)
		self.assertEqual(op.encoded_size(0,0), 1)

		# A SourceRead with a longer length spills over into two bytes.
		op = ops.SourceRead(33)
		self.assertEqual(op.encoded_size(0,0), 2)

		# The encoded size is independant of copy offsets.
		self.assertEqual(op.encoded_size(1000, 1000), 2)

	def test_equality(self):
		"""
		SourceRead ops are only equal if their properties are equal.
		"""
		op1 = ops.SourceRead(5)
		op2 = ops.SourceRead(5)
		self.assertEqual(op1, op2)

		op3 = ops.SourceRead(6)
		self.assertNotEqual(op1, op3)

		self.assertNotEqual(op1, 5)

	def test_marker(self):
		"""
		SourceRead ops use the marker 'sr'.
		"""
		op = ops.SourceRead(1)
		self.assertEqual(op.marker, 'sr')

	def test_shrink_by_zero(self):
		"""
		Shrinking by zero is not allowed.
		"""
		op = ops.SourceRead(10)

		self.assertRaisesRegex(ValueError, "0 is too small",
				op.shrink, 0)

	def test_shrink_by_bytespan(self):
		"""
		Shrinking away to nothing (or less!) is not allowed, from either end.
		"""
		op = ops.SourceRead(10)

		self.assertRaisesRegex(ValueError, "10 is too large",
				op.shrink, 10)

		self.assertRaisesRegex(ValueError, "-10 is too large",
				op.shrink, -10)

	def test_shrink_from_front(self):
		"""
		SourceRead ops can be shrunk from the front.
		"""
		op = ops.SourceRead(10)
		op.shrink(5)

		self.assertEqual(ops.SourceRead(5), op)

	def test_shrink_from_behind(self):
		"""
		SourceRead ops can be shrunk from behind.
		"""
		op = ops.SourceRead(10)
		op.shrink(-5)

		self.assertEqual(ops.SourceRead(5), op)


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

	def test_efficiency(self):
		"""
		The TargetRead op's efficiency only depends on its length.
		"""
		op = ops.TargetRead(b'A')
		self.assertAlmostEqual(op.efficiency(   0,    0), 0.50, delta=0.01)
		self.assertAlmostEqual(op.efficiency(1000, 1000), 0.50, delta=0.01)

		op = ops.TargetRead(b'AAA')
		self.assertAlmostEqual(op.efficiency(   0,    0), 0.75, delta=0.01)
		self.assertAlmostEqual(op.efficiency(1000, 1000), 0.75, delta=0.01)

	def test_encoded_size(self):
		"""
		The TargetRead op's encoded size depends only on its length.
		"""
		# A short TargetRead takes a single byte, plus the payload.
		op = ops.TargetRead(b'A' * 32)
		self.assertEqual(op.encoded_size(0,0), 33)

		# A longer TargetRead takes two bytes, plus the payload.
		op = ops.TargetRead(b'A' * 33)
		self.assertEqual(op.encoded_size(0,0), 35)

		# The encoded size is independant of copy offsets.
		self.assertEqual(op.encoded_size(1000,1000), 35)

	def test_equality(self):
		"""
		TargetRead ops are equal if their payloads are equal.
		"""
		op1 = ops.TargetRead(b'AB')
		op2 = ops.TargetRead(b'AB')
		self.assertEqual(op1, op2)

		op3 = ops.TargetRead(b'A')
		op3.extend(ops.TargetRead(b'B'))
		self.assertEqual(op1, op3)

		op4 = ops.TargetRead(b'BA')
		self.assertNotEqual(op1, op4)

		self.assertNotEqual(op1, b'AB')

	def test_marker(self):
		"""
		TargetRead ops use the marker 'tR'.
		"""
		op = ops.TargetRead(b'A')
		self.assertEqual(op.marker, 'tR')

	def test_shrink_by_zero(self):
		"""
		Shrinking by zero is not allowed.
		"""
		op = ops.TargetRead(b'ABCDEFGHIJ')

		self.assertRaisesRegex(ValueError, "0 is too small",
				op.shrink, 0)

	def test_shrink_by_bytespan(self):
		"""
		Shrinking away to nothing (or less!) is not allowed, from either end.
		"""
		op = ops.TargetRead(b'ABCDEFGHIJ')

		self.assertRaisesRegex(ValueError, "10 is too large",
				op.shrink, 10)

		self.assertRaisesRegex(ValueError, "-10 is too large",
				op.shrink, -10)

	def test_shrink_from_front(self):
		"""
		TargetRead ops can be shrunk from the front.
		"""
		op = ops.TargetRead(b'ABCDEFGHIJ')
		op.shrink(5)

		self.assertEqual(ops.TargetRead(b'FGHIJ'), op)

	def test_shrink_from_behind(self):
		"""
		TargetRead ops can be shrunk from behind.
		"""
		op = ops.TargetRead(b'ABCDEFGHIJ')
		op.shrink(-5)

		self.assertEqual(ops.TargetRead(b'ABCDE'), op)


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

	def test_equality(self):
		"""
		This op is equal with another if its properties are equal.
		"""
		op1 = self.constructor(1, 1)
		op2 = self.constructor(1, 1)
		self.assertEqual(op1, op2)

		op3 = self.constructor(2, 1)
		self.assertNotEqual(op1, op3)

		op4 = self.constructor(1, 2)
		self.assertNotEqual(op1, op4)

		self.assertNotEqual(op1, (1, 1))

	def test_shrink_by_zero(self):
		"""
		Shrinking by zero is not allowed.
		"""
		op = self.constructor(10, 10)

		self.assertRaisesRegex(ValueError, "0 is too small",
				op.shrink, 0)

	def test_shrink_by_bytespan(self):
		"""
		Shrinking away to nothing (or less!) is not allowed, from either end.
		"""
		op = self.constructor(10, 10)

		self.assertRaisesRegex(ValueError, "10 is too large",
				op.shrink, 10)

		self.assertRaisesRegex(ValueError, "-10 is too large",
				op.shrink, -10)

	def test_shrink_from_front(self):
		"""
		This op can be shrunk from the front.
		"""
		op = self.constructor(10, 10)
		op.shrink(5)

		self.assertEqual(self.constructor(5, 15), op)

	def test_shrink_from_behind(self):
		"""
		This op can be shrunk from behind.
		"""
		op = self.constructor(10, 10)
		op.shrink(-5)

		self.assertEqual(self.constructor(5, 10), op)


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

	def test_efficiency(self):
		"""
		The SourceCopy op's efficiency depends on length, lastSourceCopyOffset.
		"""
		op = ops.SourceCopy(2, 0)
		self.assertAlmostEqual(op.efficiency(   0,    0), 1.00, delta=0.01)
		self.assertAlmostEqual(op.efficiency(   0, 1000), 1.00, delta=0.01)
		self.assertAlmostEqual(op.efficiency(1000,    0), 0.66, delta=0.01)

		op = ops.SourceCopy(4, 0)
		self.assertAlmostEqual(op.efficiency(   0,    0), 2.00, delta=0.01)
		self.assertAlmostEqual(op.efficiency(   0, 1000), 2.00, delta=0.01)
		self.assertAlmostEqual(op.efficiency(1000,    0), 1.33, delta=0.01)

	def test_encoded_size(self):
		"""
		The SourceCopy op's size depends on length and lastSourceCopyOffset.
		"""
		op = ops.SourceCopy(32, 0)
		self.assertEqual(op.encoded_size(63, 63), 2)
		self.assertEqual(op.encoded_size(63, 64), 2)
		self.assertEqual(op.encoded_size(64, 63), 3)

		op = ops.SourceCopy(33, 0)
		self.assertEqual(op.encoded_size(63, 63), 3)
		self.assertEqual(op.encoded_size(63, 64), 3)
		self.assertEqual(op.encoded_size(64, 63), 4)

	def test_marker(self):
		"""
		SourceCopy ops use the marker 'Sc'.
		"""
		op = ops.SourceCopy(1, 2)
		self.assertEqual(op.marker, 'Sc')


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

	def test_efficiency(self):
		"""
		The TargetCopy op's efficiency depends on length, lastTargetCopyOffset.
		"""
		op = ops.TargetCopy(2, 0)
		self.assertAlmostEqual(op.efficiency(   0,    0), 1.00, delta=0.01)
		self.assertAlmostEqual(op.efficiency(   0, 1000), 0.66, delta=0.01)
		self.assertAlmostEqual(op.efficiency(1000,    0), 1.00, delta=0.01)

		op = ops.TargetCopy(4, 0)
		self.assertAlmostEqual(op.efficiency(   0,    0), 2.00, delta=0.01)
		self.assertAlmostEqual(op.efficiency(   0, 1000), 1.33, delta=0.01)
		self.assertAlmostEqual(op.efficiency(1000,    0), 2.00, delta=0.01)

	def test_encoded_size(self):
		"""
		The TargetCopy op's size depends on length and lastTargetCopyOffset.
		"""
		op = ops.TargetCopy(32, 0)
		self.assertEqual(op.encoded_size(63, 63), 2)
		self.assertEqual(op.encoded_size(63, 64), 3)
		self.assertEqual(op.encoded_size(64, 63), 2)

		op = ops.TargetCopy(33, 0)
		self.assertEqual(op.encoded_size(63, 63), 3)
		self.assertEqual(op.encoded_size(63, 64), 4)
		self.assertEqual(op.encoded_size(64, 63), 3)

	def test_marker(self):
		"""
		TargetCopy ops use the marker 'TC'.
		"""
		op = ops.TargetCopy(1, 2)
		self.assertEqual(op.marker, 'TC')


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

	def test_efficiency(self):
		"""
		Since bytespan is zero, CRC operations have efficiency 0.
		"""
		op = self.constructor(0x11223344)
		self.assertEqual(op.efficiency(0,0), 0)

	def test_encoded_size(self):
		"""
		CRC operations always take 4 bytes.
		"""
		op = self.constructor(0x11223344)
		self.assertEqual(op.encoded_size(   0,   0), 4)
		self.assertEqual(op.encoded_size(1000,1000), 4)

	def test_equality(self):
		"""
		CRC operations are equal if their values are equal.
		"""
		op1 = self.constructor(1)
		op2 = self.constructor(1)
		self.assertEqual(op1, op2)

		op3 = self.constructor(2)
		self.assertNotEqual(op1, op3)

		self.assertNotEqual(op1, 1)

	def test_no_marker(self):
		"""
		CRC operations have no marker string.
		"""
		op = self.constructor(1)
		self.assertEqual(op.marker, None)

	def test_cannot_shrink(self):
		"""
		CRC operations cannot be shrunk.
		"""
		op = self.constructor(1)

		self.assertRaisesRegex(TypeError, "Cannot shrink",
				op.shrink, 5)


class TestSourceCRC32(CRCOperationTestsMixIn, unittest.TestCase):

	constructor = ops.SourceCRC32


class TestTargetCRC32(CRCOperationTestsMixIn, unittest.TestCase):

	constructor = ops.TargetCRC32


class TestOpBuffer(unittest.TestCase):

	def test_empty(self):
		"""
		OpBuffer starts off empty.
		"""
		ob = ops.OpBuffer()

		self.assertEqual([], list(ob))

	def test_append(self):
		"""
		OpBuffer.append() adds an operation to the buffer.
		"""
		ob = ops.OpBuffer()

		expected = [
				ops.TargetRead(b'ABC'),
				ops.SourceRead(3),
			]

		for op in expected:
			ob.append(op)

		self.assertEqual(expected, list(ob))

	def append_requires_advancement(self):
		"""
		The rollback value must be less than the operation's bytespan.
		"""
		ob = ops.OpBuffer()

		self.assertRaisesRegex(ValueError, "10 too large",
				ob.append, ops.SourceRead(10), 10)

	def test_append_with_rollback(self):
		"""
		OpBuffer.append() with a rollback value eats previous ops.
		"""
		ob = ops.OpBuffer()

		ob.append(ops.TargetRead(b'ABC') )
		ob.append(ops.SourceCopy(3, 0)   )
		ob.append(ops.SourceRead(6),    3)

		self.assertEqual(
				[
					ops.TargetRead(b'ABC'),
					ops.SourceRead(6),
				],
				list(ob),
			)

	def test_rollback_multiple_ops(self):
		"""
		Rollback can eat multiple previous ops.
		"""
		ob = ops.OpBuffer()

		ob.append(ops.TargetRead(b'ABC') )
		ob.append(ops.SourceCopy(3, 0)   )
		ob.append(ops.TargetRead(b'GHI') )
		ob.append(ops.SourceRead(7),    6)

		self.assertEqual(
				[
					ops.TargetRead(b'ABC'),
					ops.SourceRead(7),
				],
				list(ob),
			)

	def test_rollback_past_the_beginning(self):
		"""
		Trying to rollback past the first op leads to truncation.
		"""
		ob = ops.OpBuffer()
		ob.append(ops.SourceRead(6), 3)

		self.assertEqual([ops.SourceRead(3)], list(ob))

	def test_partial_TargetRead_rollback(self):
		"""
		A partial rollback eats as much TargetRead as possible.
		"""
		ob = ops.OpBuffer()

		ob.append(ops.TargetRead(b'ABCDEF'))
		ob.append(ops.SourceRead(6), 4)

		self.assertEqual(
				[
					ops.TargetRead(b'AB'),
					ops.SourceRead(6),
				],
				list(ob),
			)

	def test_partial_SourceRead_rollback(self):
		"""
		There's no point in a new copy operation eating any SourceRead bytes.
		"""
		ob = ops.OpBuffer()

		ob.append(ops.SourceRead(6))
		ob.append(ops.SourceCopy(6, 0), 3)

		self.assertEqual(
				[
					ops.SourceRead(6),
					ops.SourceCopy(3, 3),
				],
				list(ob),
			)

	def test_partial_SourceCopy_rollback(self):
		"""
		There's no point in a new copy operation eating any SourceCopy bytes.
		"""
		ob = ops.OpBuffer()

		ob.append(ops.SourceCopy(6, 0))
		ob.append(ops.SourceRead(6), 3)

		self.assertEqual(
				[
					ops.SourceCopy(6, 0),
					ops.SourceRead(3),
				],
				list(ob),
			)

	def test_partial_TargetCopy_rollback(self):
		"""
		There's no point in a new copy operation eating any TargetCopy bytes.
		"""
		ob = ops.OpBuffer()

		ob.append(ops.TargetCopy(6, 0))
		ob.append(ops.TargetCopy(6, 0), 3)

		self.assertEqual(
				[
					ops.TargetCopy(6, 0),
					ops.TargetCopy(3, 3),
				],
				list(ob),
			)

	def test_offsets_of_empty_buffer(self):
		"""
		A fresh buffer has both copy offsets set to 0.
		"""
		ob = ops.OpBuffer()

		self.assertEqual((0, 0), ob.copy_offsets())

	def test_SourceCopy_updates_SourceCopyOffset(self):
		"""
		A SourceCopy operation sets lastSourceCopyOffset.
		"""
		ob = ops.OpBuffer()
		ob.append(ops.SourceCopy(1, 3))

		self.assertEqual((4, 0), ob.copy_offsets())

	def test_TargetCopy_updates_TargetCopyOffset(self):
		"""
		A TargetCopy operation sets lastTargetCopyOffset.
		"""
		ob = ops.OpBuffer()
		ob.append(ops.TargetCopy(2, 4))

		self.assertEqual((0, 6), ob.copy_offsets())

	def test_SourceRead_does_not_affect_copy_offsets(self):
		"""
		A SourceRead operation does not change the copy offsets.
		"""
		ob = ops.OpBuffer()
		ob.append(ops.SourceRead(5))

		self.assertEqual((0, 0), ob.copy_offsets())

	def test_TargetRead_does_not_affect_copy_offsets(self):
		"""
		A TargetRead operation does not change the copy offsets.
		"""
		ob = ops.OpBuffer()
		ob.append(ops.TargetRead(b'ABC'))

		self.assertEqual((0, 0), ob.copy_offsets())

	def test_copy_offsets_with_zero_rollback(self):
		"""
		Zero rollback does not affect the reported copy offsets.
		"""
		ob = ops.OpBuffer()
		ob.append(ops.SourceCopy(5, 7))
		ob.append(ops.TargetCopy(6, 3))

		self.assertEqual((12, 9), ob.copy_offsets(0))

	def test_copy_offsets_with_partial_rollback(self):
		"""
		Partially rolling back a copy op does not affect the reported offsets.
		"""
		ob = ops.OpBuffer()
		ob.append(ops.SourceCopy(5, 7))
		ob.append(ops.TargetCopy(6, 3))

		self.assertEqual((12, 9), ob.copy_offsets(3))

	def test_copy_offsets_with_full_rollback(self):
		"""
		Rolling back past a copy op changes the reported offsets.
		"""
		ob = ops.OpBuffer()
		ob.append(ops.SourceCopy(5, 7))
		ob.append(ops.TargetCopy(6, 3))

		self.assertEqual((12, 0), ob.copy_offsets(6))


if __name__ == "__main__":
	unittest.main()
