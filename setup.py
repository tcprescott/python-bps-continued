#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

from distutils.core import setup

setup(
		name="python-blip",
		version="1",
		description="A toolkit for working with Blip patch files",
		author="Timothy Allen",
		author_email="screwtape@froup.com",
		packages=["blip"],
		scripts=[
			"bin/blip-apply",
			"bin/blip-asm",
			"bin/blip-disasm",
			"bin/blip-validate",
			],
	)
