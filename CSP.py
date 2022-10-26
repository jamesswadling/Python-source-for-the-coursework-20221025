import copy

class CSPNode(object):

      # constructor. Needs some domain for the variable 
      def __init__(self, name, domain, value=None):

          self._name = name
          # domain is a tuple of legal values 
          super(CSPNode,self).__setattr__("_domain",domain)
          # value is the actual setting of the variable
          super(CSPNode,self).__setattr__("_value",None)
          # legalValues is a set of the remaining domain after all other assignments
          super(CSPNode,self).__setattr__("_legalValues",None)
          # setting a fixed value will raise this flag and prevent changing it.
          super(CSPNode,self).__setattr__("_fixed", False)
          # illegalValues is the set of values constrained by some other variable
          super(CSPNode,self).__setattr__("_illegalValues",set([]))
          # constrainedBy is a list of constraining edges
          super(CSPNode,self).__setattr__("_constrainedBy",[])
          # an initialised domain will filter the value
          if self._domain is not None:
             super(CSPNode,self).__setattr__("_legalValues",set(domain))
             if value is not None:
                if value in domain:      
                   super(CSPNode,self).__setattr__("_value",value)
                else:
                   raise ValueError("Illegal value initialiser {0} for variable with domain {1}".format(value, domain))
                   return               
          else:
             super(CSPNode,self).__setattr__("_value",value)

      # override Python assignment; must use setters
      def __setattr__(self,name,value):

          # disable ordinary setting of the constrained properties of the object.
          if name in ('_value', '_domain', '_legalValues', '_illegalValues', '_constrainedBy','_fixed'):
             return
          else:
             super(CSPNode,self).__setattr__(name,value)

         
      def setValue(self,value):

          # setting a None value is equivalent to clearing the value
          if value is None:
             if self._value is not None:
                return self.clearValue()
             # no-op: set a None value to None
             return True
          # make sure the value to set is legal
          if self.isLegal(value):
             try:
                 # go through the constraints, trying to find one that produces an illegal
                 # value. Fail if one is found. applyConstraint will, meanwhile, trim the
                 # legal value set in its other variable.
                 badValue = next(constraint for constraint in self._constrainedBy
                                 if not constraint.applyConstraint(self, value))
                 try:
                     undoValue = next(constraint for constraint in self._constrainedBy
                                      if not constraint.clearConstraint(self, value) and
                                      constraint == badValue)
                 except StopIteration:
                        pass
                 return False
             except StopIteration:
                 super(CSPNode,self).__setattr__('_value',value)
                 return True
          return False

      def setFixedValue(self,value):

          if value == None or not self.setValue(value):
             return False
          super(CSPNode,self).__setattr__('_legalValues', set([value]))
          super(CSPNode,self).__setattr__('_illegalValues',
                                          set([iV for iV in self._domain if iV != value]))
          super(CSPNode,self).__setattr__("_fixed",True)
          return True
    
      def clearValue(self):

          # a fixed value can't be cleared
          if self._fixed:
             return False
          # no value for the variable is always a successful clear
          if self._value is None:
             return True
          if self._domain is not None:
             # temporary copy. NOTE: chance of losing the value here with Python mutable
             # objects. It's not clear whether setting a temporary variable to a mutable
             # object (which, in Python, usually results in a reference to the original
             # object), will then effectively clear the temporary if the attribute is
             # cleared. May have to do a deep copy in this situation.
             clearedValue = self._value
             # Now clear the actual value
             super(CSPNode,self).__setattr__('_value', None)           
             # creating a generator here will go through all this variable's
             # dependent variables and remove any constraint that is the result
             # of our value having been set.
             recovered = len([constraint for constraint in self._constrainedBy
                              if constraint.clearConstraint(self, clearedValue)])
             if recovered != 0:
                # clearance succeeded, which should be the usual situation.
                # But if the clearance still doesn't leave us with other options,
                # clear the least-constrained upstream variable (i.e. that constrained us)
                #if self.numLegal <= 1:
                #   return self.clearLeastConstrainedUpstreamValue()
                return True
          # bad domain
          return False

      def clearLeastConstrainedUpstreamValue(self):

            
          leastConstrained = next(l for l in self._constrainedBy[0].endPoints if l != self)
          for constraint in self._constrainedBy[1:]:
              other = next(n for n in constraint.endPoints if n != self)
              if other.numLegal < leastConstrained.numLegal:
                 leastConstrained = other
          return leastConstrained.clearValue()
          

      # usually called by applyConstraint to remove values that can't be used for this variable
      def removeLegalValue(self,value):

          # no value to remove is always a success
          if value is None:
             return True
          # already set to value implies can't remove from legal set; fail.
          if self._value == value:
             return False
          # no more legal values is equivalent to a successful removal
          if len(self._legalValues) == 0:
             return True
          # make sure the value would have been legal
          if self.isLegal(value):
             self._legalValues.remove(value)
             self._illegalValues.add(value)
          return True

      def restoreLegalValue(self,value):

          # no value to restore is equivalent to a failure
          if self._domain is not None and value is not None:
             # can't restore a value which is absolutely illegal
             if value not in self._domain:
                return False
             # immediately succeed if the value was already legal
             if self.isLegal(value):
                return True
             # need to check against all possible constraints to make sure
             # a restore should actually proceed. Any failure immediately
             # stops the restore.
             try:
                limiting = next(c for c in self._constrainedBy if not c.checkConstraint(self, value))
             except StopIteration:
                self._legalValues.add(value)
                if value in self._illegalValues:
                   self._illegalValues.remove(value)
                return True
          return False

      def isLegal(self,value):
          if self._domain is not None:
             # as long as there is a domain, an empty value is by definition legal
             if value is not None:
                # set up the legal values if it hasn't already been done.
                if len(self._legalValues) == 0 and len(self._illegalValues) == 0:
                   super(CSPNode,self).__setattr__('_legalValues',set(self._domain))
                if value in self._illegalValues:
                   if value in self._legalValues:
                      raise AttributeError("Value {0} is in both legal and illegal sets for variable {1}".format(value, self.name))
                   return False
             # succeed if the value was legal
             return True
          # no domain means everything is illegal
          return False

      def setConstraint(self, constraint):

          # irrelevant constraint that doesn't apply to this node
          if self not in constraint.endPoints:
             print("Warning: attempted to set a constraint not relating to variable {0}. Ignoring".format(self._name))
             return False
          # can only apply a constraint to a node that has a domain
          if self._domain is not None:
             # don't need to check other node if our value is clear
             if self._value is not None:
                # as usual, initialise legal values if they haven't already been 
                if len(self._legalValues) == 0 and len(self._illegalValues) == 0:
                   super(CSPNode,self).__setattr__('_legalValues',set(self._domain))
                constrainingNode = next(node for node in constraint.endPoints if node != self)
                # no need to apply the constraint if the other node is clear
                if constrainingNode.value is not None:
                   # try to constrain our value
                   if not constraint.applyConstraint(constrainingNode, constrainingNode.value):
                      # if that fails, try to clear our value
                      if not self.clearValue():
                         #  and if that fails, the constraint is absolutely unsatisfiable
                         return False
             # insert the new constraint
             self._constrainedBy.append(constraint)
             return True
          # bad domain. 
          return False

      def removeConstraint(self, constraint):

          # find the constraint to clear
          try:
              super(CSPNode,self)._constrainedBy.remove(constraint)
          except StopIteration:
          # no such constraint. No progress.
              return False
          otherNode = next(n for n in constraint if n != self)           
          if not (constraint.clearConstraint(self, self._value) and
                  constraint.clearConstraint(otherNode, otherNode.value)):
             # clearing didn't help
             return False
          # removal succeeded and added some values to the legal domain.
          return True
                 
                   
      # properties that are useful in determining most-constrained, least-constraining
      # and highest degree heuristics
      @property
      def numLegal(self):
          # no domain, no legal values
          if self._domain is None:
             return 0
          # legal values not set up. The domain gives the length.
          if len(self._legalValues) == 0 and len(self._illegalValues) == 0:
             return len(self._domain)
          return len(self._legalValues)

      @property
      def numIllegal(self):
          return len(self._illegalValues)

      @property
      def numConstraints(self):
          return len(self._constrainedBy)

      @property
      def name(self):
          return self._name
                                               
      @property
      def value(self):
          return self._value

      @property
      def legalValues(self):
          return self._legalValues

      @property
      def illegalValues(self):
          return self._illegalValues


# a CSPEdge contains an atomic constraint linking 2 nodes. A constraint is a function taking 2 values
# and returning True or False depending upon whether the values meet the constraint - i.e. if a given
# value in one node is legal given a value in another. This could be a lambda function in simple
# case; more generally it can be any function object that returns a boolean. Edges have 4 methods,
# to apply a constraint on a node based on the value in another, to clear a constraint on a node
# based on a value in the other that is no longer relevant, to check the validity of 2 values
# against a constraint, and to revise a constraint (for arc consistency)
class CSPEdge(object):

      def __init__(self, nodeA: CSPNode, nodeB: CSPNode, constraint):

          if nodeA == nodeB:
             raise ValueError("Attempt to define a self-constraint on node {0}".format(nodeA.name))
          self._endPoints = (nodeA, nodeB)
          self._constraint = constraint
          self._active = [False, False]
          self.valid = True
          if not self._endPoints[0].setConstraint(self):
             print("Invalid constraint set for node {0}".format(self._endPoints[0].name))
             self.valid = False
             return
          if not self._endPoints[1].setConstraint(self):
             print("Invalid constraint set for node {0}".format(self._endPoints[1].name))
             self.valid = False

      # impose a constraint upon a node, based on the value in the other node.
      # we just run the constraint function on the list of legal values, and
      # remove any that violate the constraint.
      def applyConstraint(self, node: CSPNode, value):
          # succeed immediately when passed a blank value; do nothing to the legal value set
          if value is None:
             return True
          other = next(n for n in self._endPoints if n != node)
          illegalValues = [i for i in other.legalValues if not self._constraint(value, i)]
          removedValues = []
          for illegal in illegalValues:
              if not other.removeLegalValue(illegal):
                 # if a removal failed, back out the already-moved values from the illegal list
                 # very tricky step here: we use a generator expression to iterate through the
                 # list exhaustively, by setting a test condition for the generator to return to
                 # a value that can't happen (restoreLegalValue() always returns True or False.
                 try:
                     e = next(r for r in removedValues if other.restoreLegalValue(r) is None)
                 except StopIteration:
                     pass
                 # fail if a value couldn't be removed; this implies the node
                 # was already set to a value in the conflict set.
                 self.valid = False
                 return False
              removedValues.append(illegal)
          self._active[self._endPoints.index(other)] = True
          return True
          
      # release a constraint on one node based on the value assumed no longer operative in
      # the other node.
      def clearConstraint(self, node: CSPNode, value):
          # regardless of what happens, this constraint is no longer active
          other = next(n for n in self._endPoints if n != node)
          self._active[self._endPoints.index(other)] = False
          # fail immediately if a blank value is given, couldn't remove anything from the illegal set
          if value is None:
             return False
          # get all the restorable values. Build a list because illegalValues is going to be changing
          nowLegalValues = [l for l in other.illegalValues if not self._constraint(value, l)]
          # This variable was never in conflict anyway. Nothing to do.
          if len(nowLegalValues) == 0:
             self.valid = True
             return True
          numRecovered = 0
          # now restore the values
          for legal in nowLegalValues:
              if other.restoreLegalValue(legal):
                 numRecovered += 1
          # gained nothing by trying to recover
          if numRecovered == 0:
             return False
          # some values were recovered
          if node.numLegal > 0 and other.numLegal > 0:
             self.valid = True
          return True

      def checkConstraint(self, node: CSPNode, value):
          # immediately succeed if the edge isn't constrained against this node                                                                          
          if not self._active[self._endPoints.index(node)] or value is None:
             return True
          other = next(n for n in self._endPoints if n != node)
          # constraint always succeeds if the other's value is clear
          if other.value is None:
             return True
          return self._constraint(other.value, value)

      def reviseConstraint(self, node: CSPNode):

          other = next(n for n in self._endPoints if n != node)
          if other.value is not None:
             legalValues = set([other.value])
          else:
             legalValues = other.legalValues
          illegal = (firstVal for firstVal in node.legalValues
                              if len([secondVal for secondVal in legalValues
                                      if self._constraint(firstVal, secondVal)]) == 0)
          finished = False
          badVals = []
          while not finished:
              try:
                  badVals.append(next(illegal))             
              except StopIteration:
                  finished = True
          for val in badVals:
              if not node.removeLegalValue(val):
                 if not node.clearValue():
                    raise ValueError("CSP is fundamentally unsolvable: fixed value {0} on node {1} conflicts".format(val, node.name))
                 node.removeLegalValue(val)
          return len(badVals) > 0

      @property
      def endPoints(self):
          return self._endPoints

      @property
      def endPointNames(self):
          return (self._endPoints[0].name, self._endPoints[1].name)

class CSPGraph(object):

      def __init__(self, nodes, edges=None, fixedNodes=None):

          super(CSPGraph,self).__setattr__('_satisfiable', True) # if satisfiable is false, the entire graph has no solution.
          # nodes are stored in a dictionary indexable by the variable name, to make
          # lookups reasonably fast.
          super(CSPGraph,self).__setattr__('_nodes', dict([(n.name,n) for n in nodes]))
          # unfortunately, edges can't be looked up in the same quick way because in general,
          # there could be multiple edges between the same 2 nodes, representing multiple constraints.
          # So edges are just a list.
          super(CSPGraph,self).__setattr__('_edges', edges)

          # try to set any fixed nodes. 
          if fixedNodes is not None:
             try:
                  failure = next(setNode for setNode in fixedNodes if not self._nodes[setNode].setFixedValue(fixedNodes[setNode]))
                  super(CSPGraph,self).__setattr__('_satisfiable', False) # if we reach this point a node set failed.
             except StopIteration:
                  pass                      # iterated through the fixed nodes: success.

      # 
      def __getattribute__(self,name):

          if name in ('_satisfiable', '_nodes', '_edges'):
             return
          else: 
             super(CSPGraph,self).__getattribute__(self,name)
      
      # override Python assignment; must use setters
      def __setattr__(self,name,value):

          # disable ordinary setting of the constrained properties of the object.
          if name in ('_satisfiable', '_nodes', '_edges'):
             return
          else:
             super(CSPGraph,self).__setattr__(name,value)

      # does what it says on the tin
      def addNode(self, node):

          if node.name in self._nodes:
             raise ValueError("Tried to add node {0}, but it already exists in the CSP".format(node.name))
          super(CSPGraph,self).__getattribute__('_nodes')[node.name] = node

      # no surprises here either.
      def addEdge(self, edge):

          super(CSPGraph,self).__getattribute__('_edges').append(edge)

      # returns failure (false) if the value couldn't be set.
      def setValue(self, node, value):

          return super(CSPGraph,self).__getattribute__('_nodes')[node].setValue(value)

      # can also set (clamp) a node to a fixed value
      def setFixed(self, node, value):

          setOK = self.getNode(node).setFixedValue(value)
          # clamping to an invalid value means the whole graph will ultimately fail
          if not setOK:
             self._satisfiable = False
          return setOK

      
      # access a node
      def getNode(self, node):

          return super(CSPGraph,self).__getattribute__('_nodes')[node]


      # get all the nodes as a list
      @property
      def nodes(self):
          return super(CSPGraph,self).__getattribute__('_nodes').values()

      @property
      def edges(self):
          return list(super(CSPGraph,self).__getattribute__('_edges'))
    
      @property
      def satisfiable(self):

          if super(CSPGraph,self).__getattribute__('_satisfiable'):
             try: 
                 edgesOK = next(edge for edge in super(CSPGraph,self).__getattribute__('_edges') if not edge.valid)
                 return False
             except StopIteration:
                 return True
          return False
