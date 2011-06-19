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
		version="3",
		description="A toolkit for working with Blip patch files",
		url="https://gitorious.org/python-blip",
		author="Timothy Allen",
		author_email="screwtape@froup.com",
		license="WTFPL",
		packages=["blip", "blip.test"],
		package_data={"blip.test": ["testdata/*"]},
		scripts=[
			"bin/blip-apply",
			"bin/blip-asm",
			"bin/blip-diff",
			"bin/blip-disasm",
			"bin/blip-optimize",
			"bin/blip-validate",
			],
	)
