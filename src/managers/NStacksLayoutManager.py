"""
Copyright 2022 Joe Maples <joe@maples.dev>

This file is part of layman.

layman is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

layman is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
layman. If not, see <https://www.gnu.org/licenses/>.
"""
from collections import deque

from .WorkspaceLayoutManager import WorkspaceLayoutManager


class NStacksLayoutManager(WorkspaceLayoutManager):
    shortName = "NStacks"
    overridesMoveBinds = True

    class Stack(WorkspaceLayoutManager):
        order = 0
        newOnTop = False
        maxCount = 2
        layout = "splitv"
        conId = 0
        windowIds = []

        def __init__(self, con, workspace, options, windowId):
            super().__init__(con, workspace, options)
            self.conId = windowId
            self.log("Initializing stack %d with window %d" % (self.order, self.conId))

        def windowAdded(self, windowId):
            if windowId in self.windowIds:
                # Don't duplicate window records
                return

            if self.conId == 0:
                self.conId = windowId

            stackCon = self.getConById(self.conId)

            if len(stackCon.nodes) == 0:
                # Initialize stack
                self.con.command("[con_id=%d] split vertical, layout %s" % (self.conId, self.layout))
                window = self.getConById(self.conId)
                self.conId = window.parent.id
                self.con.command("[con_id=%d] mark --add stack-%d" % (self.conId, self.order))
                self.windowIds.append(window.id)


            self.windowIds.append(windowId)
            self.con.command("[con_id=%d] move window to mark stack-%d" % (windowId, self.order))
            if self.newOnTop and len(self.windowIds) > 1:
                self.moveToTopOfStack(windowId)

            self.log("Added window %d to stack %d" % (windowId, self.order))

        def knownWindowRemoved(self, removedId):
            try:
                self.windowIds.remove(removedId)

                # Reset stack if empty
                if len(self.windowIds) == 0:
                    self.conId = 0

            except:
                # Not in stack
                self.log("idk")


        def windowRemoved(self):
            try:
                stackCon = self.getConById(self.conId)
                nodeIds = []

                for node in stackCon.nodes:
                    nodeIds.append(node.id)

                nodeIds = set(nodeIds)
                missingWindows = list(set(self.windowIds) - nodeIds)
                removed = False
                if len(missingWindows) > 0:
                    removed = True
                    for missingId in missingWindows:
                        self.windowIds.remove(missingId)

                # Reset stack if empty
                if len(self.windowIds) == 0:
                    self.conId = 0

                return removed
            except:
                # Not in stack
                self.log("idk")
                return False

        def moveToTopOfStack(self, windowId):
            # The top of a tabbed layout is the closest to master, handle that
            moveDirection = "up"
            topIndex = 0
            if self.layout == "tabbed":
                moveDirection = "left"

            # Get stack container
            try:
                stackCon = self.getConById(windowId).parent
            except AttributeError:
                # Window not in stack
                self.moveWindow(windowId, self.windowIds[0])
                stackCon = self.getConById(windowId).parent

            # Move the previous master to top of stack
            while stackCon is not None and stackCon.nodes[topIndex].id != windowId:
                self.con.command("[con_id=%d] move %s" % (windowId, moveDirection))
                stackCon = self.getConById(windowId).parent
                if stackCon.id != self.conId:
                    self.moveWindow(windowId, self.conId)
                    stackCon = self.getConById(self.conId)


    def __init__(self, con, workspace, options):
        super().__init__(con, workspace, options)
        self.options = options
        self.stackCount = 2
        self.stacks = []

        
    def isExcluded(self, window):
        if window is None:
            return True

        if window.type != "con":
            return True

        workspace = window.workspace()

        if workspace is None:
            return True

        if window.floating is not None and "on" in window.floating:
            return True

        if workspace.floating_nodes is not None and any(node.id == window.id for node in workspace.floating_nodes):
            return True

        return False

    def getOrder(self, stack):
        return stack.order

    def windowFocused(self, event, window):
        # Ignore excluded windows
        if self.isExcluded(window):
            return

        #topCon = self.getWorkspaceCon()
        #self.stacks.sort(key=self.getOrder)


    def windowAdded(self, event, window):
        # Ignore excluded windows
        if self.isExcluded(window):
            return
 
        topCon = self.getWorkspaceCon()

        #if len(self.stacks) >:
            # Make a stack
            # 


        if self.stackCount > len(self.stacks):
            # Make the new window a new stack if we have no stacks, or newest stack is full
            self.moveWindow(window.id, topCon.id)
            self.con.command("[con_id=%d] split none, layout splith" % window.id)
            self.log("Some stack root containers missing, creating new stack")
            self.stacks.append(self.Stack(self.con, self.getWorkspaceCon(), self.options, window.id))
            self.stacks[-1].order = len(self.stacks) - 1
            self.stacks.sort(key=self.getOrder)
        else:
            # Add new window to an existing stack
            pushedId = window.id
            for stack in reversed(self.stacks):
                stack.windowAdded(pushedId)
                if len(stack.windowIds) > stack.maxCount:
                    self.log("Stack %d full, moving bottom to next stack" % stack.order)
                    pushedId = stack.windowIds[0]
                    stack.knownWindowRemoved(pushedId)
                else:
                    break


    def windowRemoved(self, event, window):
         # Ignore excluded windows
        if self.isExcluded(window):
            return

        for stack in self.stacks:
            if stack.windowRemoved():
                if stack.order != len(self.stacks) - 1 and len(self.stacks[stack.order + 1].windowIds) > 1:
                    pullWindowId = self.stacks[stack.order + 1].windowIds[0]
                    stack.windowAdded(pullWindowId)
                    self.stacks[stack.order + 1].knownWindowRemoved(pullWindowId)
