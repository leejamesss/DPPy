from .exact_sampling import dpp_vfx_sampler


def vfx_sampler(dpp, rng, **params):
    if dpp.eval_L is None or dpp.X_data is None:
        raise ValueError('The vfx sampler is currently only available with '
                            '{"L_eval_X_data": (L_eval, X_data)} representation.')

    r_state_outer = None
    if "random_state" in params:
        r_state_outer = params.pop("random_state", None)

    sample, dpp.intermediate_sample_info = dpp_vfx_sampler(
                                        dpp.intermediate_sample_info,
                                        dpp.X_data,
                                        dpp.eval_L,
                                        random_state=rng,
                                        **params)
    if r_state_outer:
        params["random_state"] = r_state_outer

    return sample
