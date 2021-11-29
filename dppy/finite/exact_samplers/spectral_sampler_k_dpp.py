from warnings import warn

import numpy as np
import scipy.linalg as la

from dppy.finite.exact_samplers.projection_eigen_samplers import (
    select_sampler_eigen_projection,
)
from dppy.utils import check_random_state, elementary_symmetric_polynomials


def spectral_sampler_k_dpp(dpp, size, random_state=None, **params):
    assert dpp.hermitian
    if not dpp.projection:
        compute_spectral_sampler_parameters_k_dpp(dpp, size)
        return do_spectral_sampler_k_dpp(dpp, size, random_state, **params)
    else:
        eig_vals = compute_spectral_sampler_eig_vals_projection_k_dpp(dpp, size)
        # Phase 1 select_eigenvectors from eigvalues = 0 or 1
        V = dpp.eig_vecs[:, eig_vals > 0.5]
        # Phase 2
        dpp.size_k_dpp = size
        sampler = select_sampler_eigen_projection(params.get("mode"))
        return sampler(V, size=size, random_state=random_state)


def do_spectral_sampler_k_dpp(dpp, size, random_state=None, **params):
    rng = check_random_state(random_state)
    # Phase 1
    eig_vals, eig_vecs = dpp.L_eig_vals, dpp.eig_vecs
    V = select_eigen_vectors_k_dpp(
        eig_vals,
        eig_vecs,
        size=size,
        esp=dpp.esp,
        random_state=rng,
    )
    # Phase 2
    dpp.size_k_dpp = size
    sampler = select_sampler_eigen_projection(params.get("mode"))
    return sampler(V, size=size, random_state=rng)


def compute_spectral_sampler_parameters_k_dpp(dpp, size):
    """Compute eigenvalues and eigenvectors of likelihood kernel L from various parametrizations of ``dpp``

    :param dpp: ``FiniteDPP`` object
    :type dpp: FiniteDPP
    """
    while compute_spectral_sampler_parameters_k_dpp_step(dpp, size):
        pass


def compute_spectral_sampler_parameters_k_dpp_step(dpp, size):
    """
    Returns
    ``False`` if the right parameters are indeed computed
    ``True`` if extra computations are required

    Note: Sort of fixed point algorithm to find dpp.L_eig_vals and dpp.eig_vecs
    """

    if dpp.L_eig_vals is not None:
        # Phase 1
        # Precompute elementary symmetric polynomials
        if not dpp.projection:
            if dpp.esp is None or dpp.size_k_dpp < size:
                dpp.esp = elementary_symmetric_polynomials(dpp.L_eig_vals, size)
        return False

    elif dpp.K_eig_vals is not None:
        np.seterr(divide="raise")
        dpp.L_eig_vals = dpp.K_eig_vals / (1.0 - dpp.K_eig_vals)
        return True

    # Otherwise eigendecomposition is necessary
    elif dpp.L_dual is not None:
        # L_dual = Phi Phi.T = W Theta W.T
        # L = Phi.T Phi = V Gamma V.T
        # implies Gamma = Theta and V = Phi.T W Theta^{-1/2}
        phi = dpp.L_gram_factor
        eig_vals, eig_vecs = la.eigh(dpp.L_dual)
        np.fmax(eig_vals, 0.0, out=eig_vals)
        dpp.L_eig_vals = eig_vals
        dpp.eig_vecs = phi.T.dot(eig_vecs / np.sqrt(eig_vals))
        return True

    elif dpp.L is not None:
        eig_vals, dpp.eig_vecs = la.eigh(dpp.L)
        np.fmax(eig_vals, 0.0, out=eig_vals)
        dpp.L_eig_vals = eig_vals
        return True

    elif dpp.K is not None:
        eig_vals, dpp.eig_vecs = la.eigh(dpp.K)
        np.clip(eig_vals, 0.0, 1.0, out=eig_vals)
        dpp.K_eig_vals = eig_vals
        return True

    elif dpp.eval_L is not None and dpp.X_data is not None:
        # In case mode!="vfx"
        dpp.compute_L()
        return True

    else:
        raise ValueError(
            "None of the available samplers could be used based on the current DPP representation. This should never happen, please consider rasing an issue on github at https://github.com/guilgautier/DPPy/issues"
        )


def select_eigen_vectors_k_dpp(eig_vals, eig_vecs, size, esp=None, random_state=None):
    """Select columns of ``eig_vecs`` by sampling Bernoulli variables with parameters derived from the computation of elementary symmetric polynomials ``esp`` of order 0 to ``size`` evaluated in ``eig_vals``.
    This corresponds to :cite:`KuTa12` Algorithm 8.

    :param eig_vals:
        Collection of eigenvalues (assumed non-negetive)
    :type eig_vals:
        array_like

    :param eig_vecs:
        Matrix of eigenvectors stored columnwise
    :type eig_vecs:
        array_like

    :param size:
        Number of eigenvectors to be selected
    :type size:
        int

    :param esp:
        Computation of the elementary symmetric polynomials previously evaluated in ``eig_vals`` and returned by :py:func:`elementary_symmetric_polynomials <elementary_symmetric_polynomials>`, default to None.
    :type esp:
        array_like

    :return:
        Selected eigenvectors
    :rtype:
        array_like

    .. seealso::

        - :cite:`KuTa12` Algorithm 8
        - :func:`elementary_symmetric_polynomials <elementary_symmetric_polynomials>`
    """

    rng = check_random_state(random_state)

    # Size of: ground set / sample
    N, k = eig_vecs.shape[0], size

    # as in np.linalg.matrix_rank
    tol = np.max(eig_vals) * N * np.finfo(float).eps
    rank = np.count_nonzero(eig_vals > tol)
    if k > rank:
        raise ValueError("size k={} > rank(L)={}".format(k, rank))

    if esp is None:
        esp = elementary_symmetric_polynomials(eig_vals, k)

    mask = np.zeros(k, dtype=int)
    for n in range(eig_vals.size, 0, -1):
        if rng.rand() < eig_vals[n - 1] * esp[k - 1, n - 1] / esp[k, n]:
            k -= 1
            mask[k] = n - 1
            if k == 0:
                break

    return eig_vecs[:, mask]


def compute_spectral_sampler_eig_vals_projection_k_dpp(dpp, size):
    assert dpp.projection
    if dpp.kernel_type == "likelihood":
        compute_spectral_sampler_parameters_k_dpp(dpp, size)
        return dpp.L_eig_vals
    if dpp.kernel_type == "correlation":
        # check size = rank(K)
        if dpp.K_eig_vals is not None:
            rank = np.rint(np.sum(dpp.K_eig_vals)).astype(int)
        elif dpp.A_zono is not None:
            rank = dpp.A_zono.shape[0]
        else:
            dpp.compute_K()
            rank = np.rint(np.trace(dpp.K)).astype(int)

        if size != rank:
            raise ValueError(
                "k-DPP(K) with projection correlation kernel is only defined for k = rank(K), here k={} != rank={}".format(
                    size, rank
                )
            )

        if dpp.K_eig_vals is not None:
            return dpp.K_eig_vals
        if dpp.A_zono is not None:
            warn(
                "DPP defined via `A_zono`, apriori you want to use `sampl_mcmc`, but you have called `sample_exact`"
            )
            dpp.K_eig_vals = np.ones(rank)
            dpp.eig_vecs, *_ = la.qr(dpp.A_zono.T, mode="economic")
            return dpp.K_eig_vals
        else:
            dpp.compute_K()  # 0 <= K <= I
            eig_vals, dpp.eig_vecs = la.eigh(dpp.K)
            np.clip(eig_vals, 0.0, 1.0, out=eig_vals)
            dpp.K_eig_vals = eig_vals
            return dpp.K_eig_vals
