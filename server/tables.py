# vim: set ts=4 sw=4 tw=99 et:
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import awfy
import types

def get_class(field):
    try:
        identifier = globals()[field]
    except AttributeError:
        raise NameError("%s doesn't exist." % field)
    if isinstance(identifier, (types.ClassType, types.TypeType)):
        return identifier
    raise TypeError("%s is not a class." % field)

def camelcase(string):
    """Convert string or unicode from lower-case underscore to camel-case"""
    splitted_string = string.split('_')
    # use string's class to work on the string to keep its type
    class_ = string.__class__
    return class_.join('', map(class_.capitalize, splitted_string))

class DBTable:
  globalcache = {}

  def __init__(self, id):
    self.id = int(id)
    self.initialized = False
    self.cached = None

  def prefetch(self):
    if self.table() not in self.__class__.globalcache:
      self.__class__.globalcache[self.table()] = {}

    c = awfy.db.cursor()
    c.execute("SELECT *                                                         \
               FROM "+self.table()+"                                            \
               WHERE id > %s - 100 AND                                          \
                     id < %s + 100                                              \
               ", (self.id, self.id))
    for row in c.fetchall():
      cache = {}
      for i in range(len(row)):
        cache[c.description[i][0]] = row[i]
      self.__class__.globalcache[self.table()][cache["id"]] = cache

  def initialize(self):
    if self.initialized:
      return

    self.initialized = True
    if self.table() in self.__class__.globalcache:
      if self.id in self.__class__.globalcache[self.table()]:
        self.cached = self.__class__.globalcache[self.table()][self.id]
        return

    self.prefetch()
    self.cached = self.__class__.globalcache[self.table()][self.id]
    return

  def get(self, field):
    self.initialize()

    if field in self.cached:
      return self.cached[field]

    if field+"_id" in self.cached:
      id_ = self.cached[field+"_id"]
      class_ = get_class(camelcase(field))
      value = class_(id_)
      self.cached[field] = value
      return self.cached[field]
    assert False

  def update(self, data):
    sets = [key + " = " + DBTable.valuefy(data[key]) for key in data]
    c = awfy.db.cursor()
    c.execute("UPDATE "+self.table()+"                                          \
               SET "+",".join(sets)+"                                           \
               WHERE id = %s", (self.id, ))
     
  @staticmethod
  def valuefy(value):
    if "'" in str(value):
        raise TypeError("' is not allowed as value.")
    if value == "UNIX_TIMESTAMP()":
        return value
    else:
        return "'"+str(value)+"'"

  @classmethod
  def insert(class_, data):
    values = [DBTable.valuefy(value) for value in data.values()]
    c = awfy.db.cursor()
    c.execute("INSERT INTO "+class_.table()+"                                  \
               ("+",".join(data.keys())+")                                     \
               VALUES ("+",".join(values)+")")
    return c.lastrowid

  @classmethod
  def maybeflush(class_):
    #TODO
    records = 0
    for i in class_.globalcache:
        records += len(class_.globalcache[i].keys())

class Run(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_run"

  def initialize(self):
    if self.initialized:
      return
    DBTable.initialize(self)
    if "machine_id" not in self.cached:
       self.cached["machine_id"] = self.cached["machine"]
       del self.cached["machine"]

  def getScoresAndBreakdowns(self):
    c = awfy.db.cursor()
    c.execute("SELECT id                                                              \
               FROM awfy_build                                                        \
               WHERE run_id = %s", (self.id,))
    scores = []
    for row in c.fetchall():
      scores += Build(row[0]).getScoresAndBreakdowns()
    return scores

  def getScores(self):
    c = awfy.db.cursor()
    c.execute("SELECT id                                                              \
               FROM awfy_build                                                        \
               WHERE run_id = %s", (self.id,))
    scores = []
    for row in c.fetchall():
      scores += Build(row[0]).getScores()
    return scores

  def finishStamp(self):
    pass

class SuiteTest(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_suite_test"

class SuiteVersion(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_suite_version"

class Suite(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_suite"

class Machine(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_machine"

class Mode(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_mode"

class Regression(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_regression"

class RegressionScore(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_regression_score"

class RegressionBreakdown(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_regression_breakdown"

class RegressionStatus(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_regression_status"

class Build(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_build"

  def getScores(self):
    scores = []
    c = awfy.db.cursor()
    c.execute("SELECT id                                                              \
               FROM awfy_score                                                        \
               WHERE build_id = %s", (self.id,))
    for row in c.fetchall():
      scores.append(Score(row[0]))
    return scores

  def getScoresAndBreakdowns(self):
    scores = self.getScores()
    c = awfy.db.cursor()
    c.execute("SELECT id                                                              \
               FROM awfy_breakdown                                                    \
               WHERE build_id = %s", (self.id,))
    for row in c.fetchall():
      scores.append(Breakdown(row[0]))
    return scores

class RegressionTools(DBTable):
  def __init__(self, id):
    DBTable.__init__(self, id)

  def next(self):
    self.initialize()
    if "next" not in self.cached:
        self.cached["next"] = self.compute_next()
    return self.cached["next"]

  def compute_next(self):
    nexts = self.prefetch_next(10)
    
    prev = self
    prev.cached["next"] = None
    for score in nexts:
       prev.initialize()
       prev.cached["next"] = score
       score.initialize()
       score.cached["prev"] = prev
       prev = score

    return self.cached["next"]

  def prev(self):
    self.initialize()
    if "prev" not in self.cached:
        self.cached["prev"] = self.compute_prev()
        if self.cached["prev"]:
            self.cached["prev"].initialize()
            self.cached["prev"].cached["next"] = self
    else:
        pass
    return self.cached["prev"]

  def compute_prev(self):
    prevs = self.prefetch_prev(10)
    
    next_ = self
    next_.cached["prev"] = None
    for score in prevs:
       next_.initialize()
       next_.cached["prev"] = score
       score.initialize()
       score.cached["next"] = next_
       next_ = score

    return self.cached["prev"]

  def prevs(self, amount):
    prevs = []
    point = self
    for i in range(amount):
        point = point.prev()
        if not point:
            break
        prevs.append(point)
    return prevs

  def nexts(self, amount):
    nexts = []
    point = self
    for i in range(amount):
        point = point.next()
        if not point:
            break
        nexts.append(point)
    return nexts

  def change(self):
    self.initialize()
    if "change" not in self.cached:
        self.cached["change"] = self.compute_change()
    return self.cached["change"]

  def compute_change(self):
    "Compute the change in runs before and after the current run"
    # How many runs do we need to test?
    runs = self.runs()

    # Get scores before and after this run.    
    prevs = [i.get('score') for i in self.prevs(runs)]
    nexts = [self.get('score')] + [i.get('score') for i in self.nexts(runs - 1)]

    p_weight = [len(prevs)-i for i in range(len(prevs))]
    n_weight = [len(prevs)-i for i in range(len(prevs))]
    prevs = [prevs[i]*p_weight[i] for i in range(len(prevs))]
    nexts = [nexts[i]*n_weight[i] for i in range(len(nexts))]

    # Not enough data to compute change.
    if len(nexts) != runs:
        return None
    
    # Handle edge cases.
    if sum(prevs) == 0 and sum(nexts) == 0:
        return 0
    if sum(prevs) == 0 or sum(nexts) == 0:
        return float("inf")

    avg_prevs = sum(prevs)/len(prevs)
    avg_nexts = sum(nexts)/len(nexts)

    avg_prevs /= sum(p_weight) 
    avg_nexts /= sum(n_weight) 

    change = (avg_prevs - avg_nexts) / (avg_prevs + avg_nexts)
    change = (avg_prevs - avg_nexts) / (avg_prevs)
    #return abs(change)
    return change

class Score(RegressionTools):
  def __init__(self, id):
    RegressionTools.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_score"
  
  def prefetch_next(self, limit = 1):
    stamp = self.get("build").get("run").get("stamp")
    machine = self.get("build").get("run").get("machine_id")
    mode = self.get("build").get("mode_id")
    suite = self.get("suite_version_id")

    c = awfy.db.cursor()
    c.execute("SELECT awfy_score.id                                                   \
               FROM awfy_score                                                        \
               INNER JOIN awfy_build ON awfy_build.id = awfy_score.build_id           \
               INNER JOIN awfy_run ON awfy_run.id = awfy_build.run_id                 \
               WHERE stamp > %s AND                                                   \
                     machine = %s AND                                                 \
                     mode_id = %s AND                                                 \
                     suite_version_id = %s AND                                        \
                     status = 1                                                       \
               ORDER BY stamp ASC                                                     \
               LIMIT "+str(limit), (stamp, machine, mode, suite))
    rows = c.fetchall()
    return [Score(row[0]) for row in rows]

  def prefetch_prev(self, limit = 1):
    stamp = self.get("build").get("run").get("stamp")
    machine = self.get("build").get("run").get("machine_id")
    mode = self.get("build").get("mode_id")
    suite = self.get("suite_version_id")

    c = awfy.db.cursor()
    c.execute("SELECT awfy_score.id                                                   \
               FROM awfy_score                                                        \
               INNER JOIN awfy_build ON awfy_build.id = awfy_score.build_id           \
               INNER JOIN awfy_run ON awfy_run.id = awfy_build.run_id                 \
               WHERE stamp < %s AND                                                   \
                     machine = %s AND                                                 \
                     mode_id = %s AND                                                 \
                     suite_version_id = %s AND                                        \
                     status = 1                                                       \
               ORDER BY stamp DESC                                                    \
               LIMIT 1", (stamp, machine, mode, suite))
    rows = c.fetchall()
    return [Score(row[0]) for row in rows]

  def runs(self):
    runs = max(1, self.get('build').get('run').get('machine').get("confidence_runs"))
    runs *= self.get('suite_version').get('suite').get("confidence_factor")
    runs = int(round(runs))
    return runs

  def noise(self):
    return 1.0

  def dump(self):
    if self.get("build").get("mode").get("name") != "Ion":
        return
    import datetime
    print datetime.datetime.fromtimestamp(
        int(self.get("build").get("run").get("stamp"))
    ).strftime('%Y-%m-%d %H:%M:%S'),
    print "", self.get("build").get("run").get("machine").get("description"), 
    print "", self.get("build").get("mode").get("name"),
    print "", self.get("suite_version").get("name")+":", self.change(),
    print "", self.prev().get("score") if self.prev() else "", self.get("score"),
    print " ("+str(self.runs())+" runs, "+str(self.noise())+")"

class Breakdown(RegressionTools):
  def __init__(self, id):
    RegressionTools.__init__(self, id)

  @staticmethod
  def table():
    return "awfy_breakdown"
  
  def prefetch_next(self, limit = 1):
    stamp = self.get("build").get("run").get("stamp")
    machine = self.get("build").get("run").get("machine_id")
    mode = self.get("build").get("mode_id")
    suite = self.get("suite_test_id")

    c = awfy.db.cursor()
    c.execute("SELECT awfy_breakdown.id                                               \
               FROM awfy_breakdown                                                    \
               INNER JOIN awfy_build ON awfy_build.id = awfy_breakdown.build_id       \
               INNER JOIN awfy_run ON awfy_run.id = awfy_build.run_id                 \
               WHERE stamp > %s AND                                                   \
                     machine = %s AND                                                 \
                     mode_id = %s AND                                                 \
                     suite_test_id = %s AND                                           \
                     status = 1                                                       \
               ORDER BY stamp ASC                                                     \
               LIMIT "+str(limit), (stamp, machine, mode, suite))
    rows = c.fetchall()
    return [Breakdown(row[0]) for row in rows]

  def prefetch_prev(self, limit = 1):
    stamp = self.get("build").get("run").get("stamp")
    machine = self.get("build").get("run").get("machine_id")
    mode = self.get("build").get("mode_id")
    suite = self.get("suite_test_id")

    c = awfy.db.cursor()
    c.execute("SELECT awfy_breakdown.id                                               \
               FROM awfy_breakdown                                                    \
               INNER JOIN awfy_build ON awfy_build.id = awfy_breakdown.build_id       \
               INNER JOIN awfy_run ON awfy_run.id = awfy_build.run_id                 \
               WHERE stamp < %s AND                                                   \
                     machine = %s AND                                                 \
                     mode_id = %s AND                                                 \
                     suite_test_id = %s AND                                           \
                     status = 1                                                       \
               ORDER BY stamp DESC                                                    \
               LIMIT "+str(limit), (stamp, machine, mode, suite))
    rows = c.fetchall()
    return [Breakdown(row[0]) for row in rows]

  def runs(self):
    runs = max(1, self.get('build').get('run').get('machine').get("confidence_runs"))
    runs *= self.get('suite_test').get("confidence_factor")
    runs = int(round(runs))
    return runs

  def noise(self):
    return self.get('suite_test').get("noise") * 1.

  def dump(self):
    import datetime
    print datetime.datetime.fromtimestamp(
        int(self.get("build").get("run").get("stamp"))
    ).strftime('%Y-%m-%d %H:%M:%S'),
    print "", self.get("build").get("run").get("machine").get("description"), 
    print "", self.get("build").get("mode").get("name"),
    print "", self.get("suite_test").get("suite_version").get("name")+":", self.get("suite_test").get("name")+":", self.change(),
    print "", self.prev().get("score") if self.prev() else "", self.get("score"),
    print " ("+str(self.runs())+" runs, "+str(self.noise())+")"
