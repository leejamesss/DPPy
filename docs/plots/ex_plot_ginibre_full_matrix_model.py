from dppy.beta_ensembles.ginibre import GinibreEnsemble

ginibre = GinibreEnsemble()  # beta must be 2 (default)

ginibre.sample_full_model(size_N=40)
ginibre.plot(normalization=True)

ginibre.sample_full_model(size_N=1000)
ginibre.hist(normalization=True)
