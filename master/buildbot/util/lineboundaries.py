# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

from __future__ import annotations

import re

from twisted.logger import Logger

log = Logger()


class LineBoundaryFinder:
    __slots__ = ['partialLine', 'warned']
    # split at reasonable line length.
    # too big lines will fill master's memory, and slow down the UI too much.
    MAX_LINELENGTH = 4096
    # the lookahead here (`(?=.)`) ensures that `\r` doesn't match at the end
    # of the buffer
    # we also convert cursor control sequence to newlines
    # and ugly \b+ (use of backspace to implement progress bar)
    newline_re = re.compile(r'(\r\n|\r(?=.)|\033\[u|\033\[[0-9]+;[0-9]+[Hf]|\033\[2J|\x08+)')

    def __init__(self, callback=None) -> None:
        self.partialLine: str | None = None
        self.warned: bool = False

    def adjust_line(self, text: str) -> str | None:
        if self.partialLine:
            if len(self.partialLine) > self.MAX_LINELENGTH:
                if not self.warned:
                    # Unfortunately we cannot give more hint as per which log that is
                    log.warn(
                        "Splitting long line: {line_start} {length} "
                        "(not warning anymore for this log)",
                        line_start=self.partialLine[:30],
                        length=len(self.partialLine),
                    )
                    self.warned = True
                # switch the variables, and return previous _partialLine_,
                # split every MAX_LINELENGTH plus a trailing \n
                self.partialLine, text = text, self.partialLine
                ret = []
                while len(text) > self.MAX_LINELENGTH:
                    ret.append(text[: self.MAX_LINELENGTH])
                    text = text[self.MAX_LINELENGTH :]
                ret.append(text)
                result = "\n".join(ret) + "\n"
                return result
            text = self.partialLine + text
            self.partialLine = None
        text = self.newline_re.sub('\n', text)
        if text:
            if text[-1] != '\n':
                i = text.rfind('\n')
                if i >= 0:
                    i = i + 1
                    self.partialLine = text[i:]
                    text = text[:i]
                else:
                    self.partialLine = text
                    return None
            return text
        return None

    def append(self, text: str) -> str | None:
        return self.adjust_line(text)

    def flush(self) -> str | None:
        if self.partialLine is not None:
            return self.append('\n')
        return None
