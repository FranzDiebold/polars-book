#!/usr/bin/env python
# coding: utf-8

# In[1]:


import polars as pl


# # Expressions
# 
# `fn(Series) -> Series`
# 
# * Lazily evaluated
#     - Can be optimized
#     - Gives the library writer context and informed decision can be made
# * Embarassingly parallel
# * Context dependent
#     - selection / projection -> `Series` = **COLUMN, LITERAL or VALUE**
#     - aggregation -> `Series` = **GROUPS**
# 

# In[2]:


df = pl.DataFrame(
    {
        "A": [1, 2, 3, 4, 5],
        "fruits": ["banana", "banana", "apple", "apple", "banana"],
        "B": [5, 4, 3, 2, 1],
        "cars": ["beetle", "audi", "beetle", "beetle", "beetle"],
        "optional": [28, 300, None, 2, -30],
    }
)
df


# # Selection context

# In[3]:


# We can select by name
(df.select([
    pl.col("A"),
    "B",      # the col part is inferred
    pl.lit("B"),  # we must tell polars we mean the literal "B"
    pl.col("fruits"),
]))


# In[4]:


# you can select columns with a regex if it starts with '^' and ends with '$'

(df.select([
    pl.col("^A|B$").sum()
]))


# In[5]:


# you can select multiple columns by name

(df.select([
    pl.col(["A", "B"]).sum()
]))


# In[6]:


# We select everything in normal order
# Then we select everything in reversed order
(df.select([
    pl.all(),
    pl.all().reverse().suffix("_reverse")
]))


# In[7]:


# all expressions run in parallel
# single valued `Series` are broadcasted to the shape of the `DataFrame`
(df.select([
    pl.all(),
    pl.all().sum().suffix("_sum")
]))


# In[8]:


# there are `str` and `dt` namespaces for specialized functions

predicate = pl.col("fruits").str.contains("^b.*")

(df.select([
    predicate
]))


# In[9]:


# use the predicate to filter

df.filter(predicate)


# In[10]:


# predicate expressions can be used to filter

(df.select([
    pl.col("A").filter(pl.col("fruits").str.contains("^b.*")).sum(),
    (pl.col("B").filter(pl.col("cars").str.contains("^b.*")).sum() * pl.col("B").sum()).alias("some_compute()"),
]))


# In[11]:


# We can do arithmetic on columns and (literal) values

# can be evaluated to 1 without programmer knowing
some_var = 1

(df.select([
    ((pl.col("A") / 124.0 * pl.col("B")) / pl.sum("B") * some_var).alias("computed")
]))


# In[12]:


# We can combine columns by a predicate

(df.select([
    "fruits",
    "B",
    pl.when(pl.col("fruits") == "banana").then(pl.col("B")).otherwise(-1).alias("b")
]))


# In[13]:


# We can combine columns by a fold operation on column level

(df.select([
    "A",
    "B",
    pl.fold(0, lambda a, b: a + b, [pl.col("A"), "B", pl.col("B")**2, pl.col("A") / 2.0]).alias("fold")
]))


# In[15]:


# even combine all

(df.select([
    pl.arange(0, df.height).alias("idx"),
    "A",
    pl.col("A").shift().alias("A_shifted"),
    pl.concat_str(pl.all(), "-").alias("str_concat_1"),  # prefer this
    pl.fold(pl.col("A"), lambda a, b: a + "-" + b, pl.all().exclude("A")).alias("str_concat_2"),  # over this (accidentally O(n^2))
]))


# # Aggregation context
# * expression are applied over groups instead of columns

# In[16]:


# we can still combine many expressions

(df.sort("cars").groupby("fruits")
    .agg([
        pl.col("B").sum(),
        pl.sum("B").alias("B_sum2"),  # syntactic sugar for the first
        pl.first("fruits"),
        pl.count("A").alias("count"),
        pl.col("cars").reverse()
    ]))


# In[17]:


# We can explode the list column "cars"

(df.sort("cars").groupby("fruits")
    .agg([
        pl.col("B").sum(),
        pl.sum("B").alias("B_sum2"),  # syntactic sugar for the first
        pl.first("fruits"),
        pl.count("A").alias("count"),
        pl.col("cars").reverse()
    ])).explode("cars")


# In[18]:


(df.groupby("fruits")
    .agg([
        pl.col("B").sum(),
        pl.sum("B").alias("B_sum2"),  # syntactic sugar for the first
        pl.first("fruits"),
        pl.count("A").alias("count"),
        pl.col("B").shift().alias("B_shifted")
    ])
 .explode("B_shifted")
)


# In[19]:


# we can also get the list of the groups
(df.groupby("fruits")
    .agg([
         pl.col("B").shift().alias("shift_B"),
         pl.col("B").reverse().alias("rev_B"),
    ]))


# In[20]:


# we can do predicates in the groupby as well

(df.groupby("fruits")
    .agg([
        pl.col("B").filter(pl.col("B") > 1).list().keep_name(),
    ]))


# In[21]:


# and sum only by the values where the predicates are true

(df.groupby("fruits")
    .agg([
        pl.col("B").filter(pl.col("B") > 1).mean(),
    ]))


# In[22]:


# Another example
(df.groupby("fruits")
    .agg([
        pl.col("B").shift_and_fill(1, fill_value=0).alias("shifted"),
        pl.col("B").shift_and_fill(1, fill_value=0).sum().alias("shifted_sum"),
    ]))


# # Window functions!
# 
# * Expression with superpowers.
# * Aggregation in selection context
# 
# 
# ```python
# pl.col("foo").aggregation_expression(..).over("column_used_to_group")
# ```
# 

# In[23]:


# groupby 2 different columns

(df.sort("fruits")
.select([
    "fruits",
    "cars",
    "B",
    pl.col("B").sum().over("fruits").alias("B_sum_by_fruits"),
    pl.col("B").sum().over("cars").alias("B_sum_by_cars"),
]))


# In[25]:


# reverse B by groups and show the results in original DF

(df.sort("fruits")
.select([
    "fruits",
    "B",
    pl.col("B").reverse().over("fruits").flatten().alias("B_reversed_by_fruits")
]))


# In[26]:


# Lag a column within "fruits"
(df
.sort("fruits")
.select([
    "fruits",
    "B",
    pl.col("B").shift().over("fruits").flatten().alias("lag_B_by_fruits")
]))

