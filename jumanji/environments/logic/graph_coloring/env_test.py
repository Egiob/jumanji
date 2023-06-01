# Copyright 2022 InstaDeep Ltd. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import chex
import jax
import jax.numpy as jnp

from jumanji.environments.logic.graph_coloring import GraphColoring
from jumanji.environments.logic.graph_coloring.types import State
from jumanji.testing.env_not_smoke import check_env_does_not_smoke
from jumanji.testing.pytrees import assert_is_jax_array_tree
from jumanji.types import TimeStep


def test_graph_coloring_reset_jit(graph_coloring: GraphColoring) -> None:
    """Confirm that the reset method is only compiled once when jitted."""
    chex.clear_trace_counter()
    reset_fn = jax.jit(chex.assert_max_traces(graph_coloring.reset, n=1))
    key = jax.random.PRNGKey(0)
    state, timestep = reset_fn(key)

    # Verify the data type of the output.
    assert isinstance(timestep, TimeStep)
    assert isinstance(state, State)

    # Check that the state is made of DeviceArrays, this is false for the non-jitted.
    assert_is_jax_array_tree(state.adj_matrix)
    assert_is_jax_array_tree(state.colors)

    # Call again to check it does not compile twice.
    state, timestep = reset_fn(key)
    assert isinstance(timestep, TimeStep)
    assert isinstance(state, State)


def test_graph_coloring_step_jit(graph_coloring: GraphColoring) -> None:
    """Confirm that the step is only compiled once when jitted."""
    key = jax.random.PRNGKey(0)
    state, timestep = jax.jit(graph_coloring.reset)(key)
    action = jnp.array(0)

    chex.clear_trace_counter()
    step_fn = jax.jit(chex.assert_max_traces(graph_coloring.step, n=1))

    new_state, next_timestep = step_fn(state, action)

    # Check that the state has changed.
    assert not jnp.array_equal(new_state.colors, state.colors)

    # Check that the state is made of DeviceArrays, this is false for the non-jitted.
    assert_is_jax_array_tree(new_state)

    # New step
    state = new_state
    new_state, next_timestep = step_fn(state, action)

    # Check that the state has changed
    assert not jnp.array_equal(new_state.colors, state.colors)


def test_graph_coloring_get_action_mask(graph_coloring: GraphColoring) -> None:
    """Verify that the action mask generated by `_get_valid_actions` is correct."""
    key = jax.random.PRNGKey(0)
    state, _ = graph_coloring.reset(key)
    num_nodes = graph_coloring.generator.num_nodes
    get_valid_actions_fn = jax.jit(graph_coloring._get_valid_actions)
    action_mask = get_valid_actions_fn(
        state.current_node_index, state.adj_matrix, state.colors
    )

    # Check that the action mask is a boolean array with the correct shape.
    assert action_mask.dtype == jnp.bool_
    assert action_mask.shape == (num_nodes,)

    # For this specific test case, we don't have any pre-defined expected action_mask,
    # as the graph and colors are randomly generated.


def test_graph_coloring_does_not_smoke(graph_coloring: GraphColoring) -> None:
    """Test that we can run an episode without any errors."""
    check_env_does_not_smoke(graph_coloring)
