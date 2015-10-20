import numpy as np
import six
from six.moves import range

from .base import CLOSED_BOUNDARY
from .base import BAD_INDEX_VALUE
from .raster_gradients import (calculate_gradient_across_cell_faces,
                               calculate_gradient_across_cell_corners,
                               calculate_gradient_along_node_links)


_VALID_ROUTING_METHODS = set(['d8', 'd4'])


def _assert_valid_routing_method(method):
    """Check if name is a valid routing method.

    Parameters
    ----------
    method : str
        Name of a routing method.

    Raises
    ------
    ValueError
        If the method name is invalid.
    """
    if method not in _VALID_ROUTING_METHODS:
        raise ValueError(
            '%s: routing method not understood. should be one of %s' %
            (method, ', '.join(_VALID_ROUTING_METHODS)))


def _make_optional_arg_into_array(number_of_elements, *args):
    """Transform an optional argument into an array.

    Parameters
    ----------
    number_of_elements : int
        Number of elements in the grid.
    array : array_like
        Iterable to convert to an array.

    Returns
    -------
    ndarray
        Input array converted to a numpy array, or a newly-created numpy
        array.

    Examples
    --------
    >>> import numpy as np
    >>> from landlab.grid.raster_funcs import _make_optional_arg_into_array
    >>> _make_optional_arg_into_array(4)
    array([0, 1, 2, 3])
    >>> _make_optional_arg_into_array(4, [0, 0, 0, 0])
    [0, 0, 0, 0]
    >>> _make_optional_arg_into_array(4, (1, 1, 1, 1))
    [1, 1, 1, 1]
    >>> _make_optional_arg_into_array(4, np.ones(4))
    array([ 1.,  1.,  1.,  1.])
    """
    if len(args) >= 2:
        raise ValueError('Number of arguments must be 0 or 1.')

    if len(args) == 0:
        ids = np.arange(number_of_elements)
    else:
        ids = args[0]
        if not isinstance(ids, list) and not isinstance(ids, np.ndarray):
            try:
                ids = list(ids)
            except TypeError:
                ids = [ids]
    return ids


def calculate_steepest_descent_across_adjacent_cells(grid, node_values, *args,
                                                     **kwds):
    """calculate_steepest_descent_across_adjacent_cells(grid, node_values, [cell_ids], method='d4', out=None)
    Get steepest gradient to neighbor and diagonal cells.

    Calculate the steepest downward gradients in *node_values*, given at every
    node in the grid, relative to the nodes centered at *cell_ids*. Note that
    upward gradients are reported as positive, so this method returns negative
    numbers.

    If *cell_ids* is not provided, calculate the maximum gradient for all
    cells in the grid.

    The default is to only consider neighbor cells to the north, south, east,
    and west. To also consider gradients to diagonal nodes, set the *method*
    keyword to *d8* (the default is *d4*).

    Use the *out* keyword if you have an array that you want to put the result
    into. If not given, create a new array.

    Use the *return_node* keyword to also the node id of the node in the
    direction of the maximum gradient.

    Parameters
    ----------
    grid : RasterModelGrid
        Input grid.
    node_values : array_like
        Values to take gradient of.
    cell_ids : array_link, optional
        IDs of grid cells to measure gradients.
    return_node: boolean, optional
        Return node IDs of the node that has the steepest descent.
    method : {'d4', 'd8'}
        How to calculate the steepest descent.
    out : ndarray, optional
        Alternative output array in which to place the result.  Must
        be of the same shape and buffer length as the expected output.

    Returns
    -------
    ndarray :
        Calculated gradients to lowest adjacent node.

    Examples
    --------
    Create a rectilinear grid that is 3 nodes by 3 nodes and so has one cell
    centered around node 4.

    >>> from landlab import RasterModelGrid
    >>> from landlab.grid.raster_funcs import (
    ...     calculate_steepest_descent_across_adjacent_cells)
    >>> rmg = RasterModelGrid(3, 3)
    >>> values_at_nodes = np.array([-3., -1., 0., 0., 1., 0., 0., 0., 0.])

    Calculate gradients to cell diagonals and choose the gradient to the
    lowest node.

    >>> from math import sqrt
    >>> calculate_steepest_descent_across_adjacent_cells(rmg, values_at_nodes,
    ...     method='d4')
    masked_array(data = [-2.],
                 mask = False,
           fill_value = 1e+20)
    <BLANKLINE>
    >>> calculate_steepest_descent_across_adjacent_cells(rmg, values_at_nodes,
    ...     method='d8') * sqrt(2.)
    masked_array(data = [-4.],
                 mask = False,
           fill_value = 1e+20)
    <BLANKLINE>

    With the 'd4' method, the steepest gradient is to the bottom node (id = 1).

    >>> (_, ind) = calculate_steepest_descent_across_adjacent_cells(rmg,
    ...                values_at_nodes, return_node=True)
    >>> ind
    array([1])

    With the 'd8' method, the steepest gradient is to the lower-left node
    (id = 0).

    >>> (_, ind) = calculate_steepest_descent_across_adjacent_cells(rmg,
    ...                values_at_nodes, return_node=True, method='d8')
    >>> ind
    array([0])
    """
    method = kwds.pop('method', 'd4')
    _assert_valid_routing_method(method)

    if method == 'd4':
        return calculate_steepest_descent_across_cell_faces(
            grid, node_values, *args, **kwds)
    elif method == 'd8':
        neighbor_grads = calculate_steepest_descent_across_cell_faces(
            grid, node_values, *args, **kwds)
        diagonal_grads = calculate_steepest_descent_across_cell_corners(
            grid, node_values, *args, **kwds)

        return_node = kwds.pop('return_node', False)

        if not return_node:
            return np.choose(neighbor_grads <= diagonal_grads,
                             (diagonal_grads, neighbor_grads), **kwds)
        else:
            min_grads = np.choose(neighbor_grads[0] <= diagonal_grads[0],
                                  (diagonal_grads[0], neighbor_grads[0]),
                                  **kwds)
            node_ids = np.choose(neighbor_grads[0] <= diagonal_grads[0],
                                 (diagonal_grads[1], neighbor_grads[1]),
                                 **kwds)
            return (min_grads, node_ids)


def calculate_steepest_descent_across_cell_corners(grid, node_values, *args,
                                                   **kwds):
    """calculate_steepest_descent_across_cell_corners(grid, node_values [, cell_ids], return_node=False, out=None)
    Get steepest gradient to the diagonals of a cell.

    Calculate the gradients in *node_values* measure to the diagonals of cells
    IDs, *cell_ids*. Slopes upward from the cell are reported as positive.
    If *cell_ids* is not given, calculate gradients for all cells.

    Use the *return_node* keyword to return a tuple, with the first element
    being the gradients and the second the node id of the node in the direction
    of the minimum gradient, i.e., the steepest descent. Note the gradient
    value returned is probably thus negative.

    Parameters
    ----------
    grid : RasterModelGrid
        Input grid.
    node_values : array_like
        Values to take gradient of.
    cell_ids : array_link, optional
        IDs of grid cells to measure gradients.
    return_node: boolean, optional
        If `True`, return node IDs of the node that has the steepest descent.
    out : ndarray, optional
        Alternative output array in which to place the result.  Must
        be of the same shape and buffer length as the expected output.

    Returns
    -------
    ndarray :
        Calculated gradients to lowest node across cell faces.

    Examples
    --------
    Create a rectilinear grid that is 3 nodes by 3 nodes and so has one cell
    centered around node 4.

    >>> from landlab import RasterModelGrid
    >>> from landlab.grid.raster_funcs import (
    ...     calculate_steepest_descent_across_cell_corners)
    >>> rmg = RasterModelGrid(3, 3)
    >>> values_at_nodes = np.arange(9.)

    Calculate gradients to cell diagonals and choose the gradient to the
    lowest node.

    >>> from math import sqrt
    >>> calculate_steepest_descent_across_cell_corners(rmg,
    ...     values_at_nodes) * sqrt(2.)
    array([-4.])

    The steepest gradient is to node with id 0.

    >>> (_, ind) = calculate_steepest_descent_across_cell_corners(rmg,
    ...                values_at_nodes, return_node=True)
    >>> ind
    array([0])
    """
    return_node = kwds.pop('return_node', False)

    cell_ids = _make_optional_arg_into_array(grid.number_of_cells, *args)

    grads = calculate_gradient_across_cell_corners(grid, node_values, cell_ids)

    if return_node:
        ind = np.argmin(grads, axis=1)
        node_ids = grid.diagonal_cells[grid.node_at_cell[cell_ids], ind]
        if 'out' not in kwds:
            out = np.empty(len(cell_ids), dtype=grads.dtype)
        out[:] = grads[range(len(cell_ids)), ind]
        return (out, node_ids)
        # return (out, 3 - ind)
    else:
        return grads.min(axis=1, **kwds)


def calculate_steepest_descent_across_cell_faces(grid, node_values, *args,
                                                 **kwds):
    """calculate_steepest_descent_across_cell_faces(grid, node_values [, cell_ids], return_node=False, out=None)
    Get steepest gradient across the faces of a cell.

    This method calculates the gradients in *node_values* across all four
    faces of the cell or cells with ID *cell_ids*. Slopes upward from the
    cell are reported as positive. If *cell_ids* is not given, calculate
    gradients for all cells.

    Use the *return_node* keyword to return a tuple, with the first element
    being the gradients and the second the node id of the node in the direction
    of the minimum gradient, i.e., the steepest descent. Note the gradient
    value returned is probably thus negative.

    Parameters
    ----------
    grid : RasterModelGrid
        Input grid.
    node_values : array_like
        Values to take gradient of.
    cell_ids : array_link, optional
        IDs of grid cells to measure gradients.
    return_node: boolean, optional
        Return node IDs of the node that has the steepest descent.
    out : ndarray, optional
        Alternative output array in which to place the result.  Must
        be of the same shape and buffer length as the expected output.

    Returns
    -------
    ndarray :
        Calculated gradients to lowest node across cell faces.

    Convention: gradients positive UP

    Examples
    --------
    Create a rectilinear grid that is 3 nodes by 3 nodes and so has one cell
    centered around node 4.

    >>> from landlab import RasterModelGrid
    >>> from landlab.grid.raster_funcs import (
    ...     calculate_steepest_descent_across_cell_faces)
    >>> rmg = RasterModelGrid(3, 3)
    >>> values_at_nodes = np.arange(9.)

    Calculate gradients across each cell face and choose the gradient to the
    lowest node.

    >>> calculate_steepest_descent_across_cell_faces(rmg, values_at_nodes)
    masked_array(data = [-3.],
                 mask = False,
           fill_value = 1e+20)
    <BLANKLINE>

    The steepest gradient is to node with id 1.

    >>> (_, ind) = calculate_steepest_descent_across_cell_faces(rmg,
    ...     values_at_nodes, return_node=True)
    >>> ind
    array([1])
    """
    return_node = kwds.pop('return_node', False)

    cell_ids = _make_optional_arg_into_array(grid.number_of_cells, *args)

    grads = calculate_gradient_across_cell_faces(grid, node_values, cell_ids)

    if return_node:
        ind = np.argmin(grads, axis=1)
        node_ids = grid.get_neighbor_list()[grid.node_at_cell[cell_ids], ind]
        # node_ids = grid.neighbor_nodes[grid.node_at_cell[cell_ids], ind]
        if 'out' not in kwds:
            out = np.empty(len(cell_ids), dtype=grads.dtype)
        out[:] = grads[range(len(cell_ids)), ind]
        return (out, node_ids)
        # return (out, 3 - ind)
    else:
        return grads.min(axis=1, **kwds)


def active_link_id_of_cell_neighbor(grid, inds, *args):
    """active_link_id_of_cell_neighbor(grid, link_ids [, cell_ids])

    Return an array of the active link ids for neighbors of *cell_id* cells.
    *link_ids* is an index into the links of a cell as measured
    clockwise starting from the south.

    If *cell_ids* is not given, return neighbors for all cells in the grid.

    Parameters
    ----------
    grid : RasterModelGrid
        Source grid.
    link_inds : array_like
        IDs of links
    cell_ids : array_like, optional
        IDs of cells for which to get links

    """
    cell_ids = _make_optional_arg_into_array(grid.number_of_cells, *args)
    node_ids = grid.node_at_cell[cell_ids]
    links = grid.active_links_at_node(node_ids).T

    if not isinstance(inds, np.ndarray):
        inds = np.array(inds)

    return links[range(len(cell_ids)), inds]


def node_id_of_cell_neighbor(grid, inds, *args):
    """ node_id_of_cell_neighbor(grid, neighbor_ids [, cell_ids])

    Return an array of the node ids for neighbors of *cell_id* cells.
    *neighbor_ids* is an index into the neighbors of a cell as measured
    clockwise starting from the south.

    If *cell_ids* is not given, return neighbors for all cells in the grid.

    Parameters
    ----------
    grid : RasterModelGrid
        Input grid.
    neighbor_ids : array_like
        IDs of the neighbor nodes.
    cell_ids : array_like, optional
        IDs of cell about which to get neighbors.

    Returns
    -------
    ndarray
        Node IDs for given neighbors of cells.

    Examples
    --------
    >>> from landlab import RasterModelGrid
    >>> from landlab.grid.raster_funcs import node_id_of_cell_neighbor
    >>> grid = RasterModelGrid(4, 5, 1.0)
    >>> node_id_of_cell_neighbor(grid, 0, 0)
    array([1])

    Get the lower and the the upper neighbors for all the cells.

    >>> node_id_of_cell_neighbor(grid, 0)
    array([1, 2, 3, 6, 7, 8])
    >>> node_id_of_cell_neighbor(grid, 2)
    array([11, 12, 13, 16, 17, 18])

    As an alternative to the above, use fancy-indexing to get both sets of
    neighbors with one call.

    >>> node_id_of_cell_neighbor(grid, np.array([0, 2]), [1, 4])
    array([[ 2, 12],
           [ 7, 17]])
    """
    cell_ids = _make_optional_arg_into_array(grid.number_of_cells, *args)
    node_ids = grid.node_at_cell[cell_ids]
    neighbors = grid.get_neighbor_list(node_ids)

    if not isinstance(inds, np.ndarray):
        inds = np.array(inds)

    # return neighbors[range(len(cell_ids)), 3 - inds]
    return (
        np.take(np.take(neighbors, range(len(cell_ids)), axis=0),
                3 - inds, axis=1))


def node_id_of_cell_corner(grid, inds, *args):
    """node_id_of_cell_corner(grid, corner_ids [, cell_ids])

    Return an array of the node ids for diagonal neighbors of *cell_id* cells.
    *corner_ids* is an index into the corners of a cell as measured
    clockwise starting from the southeast.

    If *cell_ids* is not given, return neighbors for all cells in the grid.

    Parameters
    ----------
    grid : RasterModelGrid
        Input grid.
    corner_ids : array_like
        IDs of the corner nodes.
    cell_ids : array_like, optional
        IDs of cell about which to get corners

    Examples
    --------
    >>> from landlab import RasterModelGrid
    >>> from landlab.grid.raster_funcs import node_id_of_cell_corner
    >>> grid = RasterModelGrid(4, 5, 1.0)
    >>> node_id_of_cell_corner(grid, 0, 0)
    array([2])

    Get the lower-right and the the upper-left corners for all the cells.

    >>> node_id_of_cell_corner(grid, 0)
    array([2, 3, 4, 7, 8, 9])
    >>> node_id_of_cell_corner(grid, 2)
    array([10, 11, 12, 15, 16, 17])

    As an alternative to the above, use fancy-indexing to get both sets of
    corners with one call.

    >>> node_id_of_cell_corner(grid, np.array([0, 2]), [1, 4])
    array([[ 3, 11],
           [ 8, 16]])
    """
    cell_ids = _make_optional_arg_into_array(grid.number_of_cells, *args)
    node_ids = grid.node_at_cell[cell_ids]
    diagonals = grid.get_diagonal_list(node_ids)

    if not isinstance(inds, np.ndarray):
        inds = np.array(inds)

    return (
        np.take(np.take(diagonals, range(len(cell_ids)), axis=0),
                3 - inds, axis=1))
    # return diagonals[range(len(cell_ids)), 3 - inds]


def calculate_flux_divergence_at_nodes(grid, active_link_flux, out=None):
    """Net flux into or out of nodes.

    Same as calculate_flux_divergence_at_core_cells, but works with and
    returns a list of net unit fluxes that corresponds to all nodes, rather
    than just core nodes.

    Parameters
    ----------
    grid : RasterModelGrid
        Input grid.
    active_link_flux : array_like
        Flux values at links.
    out : ndarray, optional
        Alternative output array in which to place the result.  Must
        be of the same shape and buffer length as the expected output.

    See Also
    --------
    calculate_flux_divergence_at_active_cells

    Notes
    -----
    Note that we DO compute net unit fluxes at boundary nodes (even though
    these don't have active cells associated with them, and often don't have
    cells of any kind, because they are on the perimeter). It's up to the
    user to decide what to do with these boundary values.

    Example
    -------
    Calculate the gradient of values at a grid's nodes.

    >>> from landlab import RasterModelGrid
    >>> rmg = RasterModelGrid(4, 5, 1.0)
    >>> u = np.array([0., 1., 2., 3., 0.,
    ...               1., 2., 3., 2., 3.,
    ...               0., 1., 2., 1., 2.,
    ...               0., 0., 2., 2., 0.])
    >>> grad = rmg.calculate_gradients_at_active_links(u)
    >>> grad
    array([ 1.,  1., -1., -1., -1., -1., -1.,  0.,  1.,  1.,  1., -1.,  1.,
            1.,  1., -1.,  1.])

    Calculate the divergence of the gradients at each node.

    >>> flux = - grad    # downhill flux proportional to gradient
    >>> rmg.calculate_flux_divergence_at_nodes(flux)
    array([ 0., -1., -1.,  1.,  0., -1.,  2.,  4., -2.,  1., -1.,  0.,  1.,
           -4.,  1.,  0., -1.,  0.,  1.,  0.])

    If calculate_gradients_at_nodes is called inside a loop, you can
    improve speed by creating an array outside the loop. For example, do
    this once, before the loop:

    >>> df = rmg.zeros(centering='node') # outside loop
    >>> rmg.number_of_nodes
    20

    Then do this inside the loop so that the function will not have to create
    the df array but instead puts values into the *df* array.

    >>> df = rmg.calculate_flux_divergence_at_nodes(flux, out=df)
    """
    assert len(active_link_flux) == grid.number_of_active_links, \
        "incorrect length of active_link_flux array"

    # If needed, create net_unit_flux array
    if out is None:
        out = grid.empty(centering='node')
    out.fill(0.)
    net_unit_flux = out

    assert len(net_unit_flux) == grid.number_of_nodes

    flux = np.zeros(grid.number_of_links + 1)
    flux[grid.active_links] = active_link_flux * grid.dx

    net_unit_flux[:] = (
        (flux[grid.node_active_outlink_matrix2[0][:]] +
         flux[grid.node_active_outlink_matrix2[1][:]]) -
        (flux[grid.node_active_inlink_matrix2[0][:]] +
         flux[grid.node_active_inlink_matrix2[1][:]])) / grid.cellarea

    return net_unit_flux

# TODO: Functions below here still need to be refactored for speed and to
# conform to the interface standards.


def calculate_max_gradient_across_node_d4(self, u, cell_id):
    """Steepest descent using D4.

    .. note:: Deprecated since version 0.1.
        Use :func:`calculate_steepest_descent_across_cell_faces` instead

    This method calculates the gradients in u across all 4 faces of the
    cell with ID cell_id. It then returns
    the steepest (most negative) of these values, followed by its dip
    direction (e.g.: 90 180). i.e., this is a D4 algorithm. Slopes
    downward from the cell are reported as positive.

    Note that this is exactly the same as calculate_max_gradient_across_node
    except that this is d4, and the other is d8.

    This code is actually calculating slopes, not gradients.
    The max gradient is the most negative, but the max slope is the most
    positive.  So, this was updated to return the max value, not the
    min.
    """
    node_id = self.node_at_cell[cell_id]
    neighbor_nodes = self.get_neighbor_list(node_id)

    grads = (u[node_id] - u[neighbor_nodes]) / self.node_spacing
    ind = np.argmax(grads)
    angles = (90., 0., 270., 180.)

    return grads[ind], angles[ind]


def calculate_slope_aspect_bfp(xs, ys, zs):
    """Calculate slope and aspect.

    .. codeauthor:: Katy Barnhart <katherine.barnhart@colorado.edu>

    Fits a plane to the given N points with given *xs*, *ys*, and *zs* values
    using single value decomposition.

    Returns a tuple of (*slope*, *aspect*) based on the normal vector to the
    best fit plane.

    .. note::

        This function does not check if the points fall on a line, rather
        than a plane.
    """
    if not len(xs) == len(ys) == len(zs):
        raise ValueError('array must be the same length')

    # step 1: subtract the centroid from the points
    # step 2: create a 3XN matrix of the points for SVD
    # in python, the unit normal to the best fit plane is
    # given by the third column of the U matrix.
    mat = np.vstack((xs - np.mean(xs), ys - np.mean(ys), zs - np.mean(zs)))
    U, _, _ = np.linalg.svd(mat)
    normal = U[:, 2]

    # step 3: calculate the aspect
    asp = 90.0 - np.degrees(np.arctan2(normal[1], normal[0]))
    asp = asp % 360.0

    # step 4: calculate the slope
    slp = 90.0 - np.degrees(np.arcsin(normal[2]))

    return slp, asp


def find_nearest_node(rmg, coords, mode='raise'):
    """Find the node nearest a point.

    Find the index to the node nearest the given x, y coordinates.
    Coordinates are provided as numpy arrays in the *coords* tuple.
    *coords* is tuple of coordinates, one for each dimension.

    The *mode* keyword to indicate what to do if a point is outside of the
    grid. Valid choices are the same as that used with the numpy function
    `ravel_multi_index`.

    A point is considered to be outside of the grid if it is outside the
    perimeter of the grid by one half of the grid spacing.

    Parameters
    ----------
    rmg : RasterModelGrid
        The source grid.
    coords : tuple
        Coordinates of point as (x, y)
    mode : {'raise', 'wrap', 'clip'}, optional
        Action to take if a point is outside of the grid.

    Returns
    -------
    array_like :
        Indices of the nodes nearest the given coordinates.

    Examples
    --------
    Create a grid of 4 by 5 nodes with unit spacing.

    >>> import landlab
    >>> from landlab.grid.raster_funcs import find_nearest_node
    >>> rmg = landlab.RasterModelGrid(4, 5)

    The points can be either a tuple of scalars or of arrays.

    >>> find_nearest_node(rmg, (0.2, 0.6))
    5
    >>> find_nearest_node(rmg, (np.array([1.6, 3.6]), np.array([2.3, .7])))
    array([12,  9])

    The *mode* keyword indicates what to do if a point is outside of the
    grid.

    >>> find_nearest_node(rmg, (-0.6, 0.6), mode='raise')
    Traceback (most recent call last):
        ...
    ValueError: invalid entry in coordinates array
    >>> find_nearest_node(rmg, (-0.6, 0.6), mode='clip')
    5
    >>> find_nearest_node(rmg, (-0.6, 0.6), mode='wrap')
    9
    """
    if isinstance(coords[0], np.ndarray):
        return _find_nearest_node_ndarray(rmg, coords, mode=mode)
    else:
        return find_nearest_node(
            rmg, (np.array(coords[0]), np.array(coords[1])), mode=mode)


def _find_nearest_node_ndarray(rmg, coords, mode='raise'):
    """Find the node nearest to a point.

    Parameters
    ----------
    rmg : RasterModelGrid
        A RasterModelGrid.
    coords : tuple of float
        Coordinates of test points as *x*, then *y*.
    mode : {'raise', 'wrap', 'clip'}, optional
        What to do with out-of-bounds indices (as with
        numpy.ravel_multi_index).

    Returns
    -------
    ndarray
        Nodes that are closest to the points.

    Examples
    --------
    >>> from landlab.grid.raster_funcs import _find_nearest_node_ndarray
    >>> from landlab import RasterModelGrid
    >>> import numpy as np
    >>> grid = RasterModelGrid((4, 5))
    >>> _find_nearest_node_ndarray(grid, (.25, 1.25))
    5
    >>> _find_nearest_node_ndarray(grid, (.75, 2.25))
    11
    """
    column_indices = np.int_(
        np.around((coords[0] - rmg.node_x[0]) / rmg.node_spacing))
    row_indices = np.int_(
        np.around((coords[1] - rmg.node_y[0]) / rmg.node_spacing))

    return rmg.grid_coords_to_node_id(row_indices, column_indices, mode=mode)


def _value_is_in_bounds(value, bounds):
    """Check if a value is within bounds.

    Parameters
    ----------
    value : float or ndarray
        The test value.
    bounds : (lower, upper)
        The lower and upper bounds.

    Returns
    -------
    bool
        ``True`` if the value is within the bounds. Otherwise, ``False``.

    Examples
    --------
    >>> from landlab.grid.raster_funcs import _value_is_in_bounds
    >>> import numpy as np
    >>> _value_is_in_bounds(.5, (0, 1))
    True
    >>> _value_is_in_bounds(1, (0, 1))
    False
    >>> _value_is_in_bounds(0, (0, 1))
    True
    >>> _value_is_in_bounds(np.array((0, 1)), (0, 1))
    array([ True, False], dtype=bool)
    """
    dummy = value >= bounds[0]
    dummy &= value < bounds[1]
    return dummy


def _value_is_within_axis_bounds(rmg, value, axis):
    """Check if a value is within the bounds of a grid axis.

    Parameters
    ----------
    rmg : RasterModelGrid
        A RasterModelGrid.
    value : float
        The test value.
    axis : int
        The axis.

    Returns
    -------
    bool
        ``True`` if the value is within the axis bounds. Otherwise, ``False``.

    Examples
    --------
    >>> from landlab.grid.raster_funcs import _value_is_within_axis_bounds
    >>> from landlab import RasterModelGrid
    >>> rmg = RasterModelGrid((4, 5))
    >>> _value_is_within_axis_bounds(rmg, 3.1, 0)
    False
    >>> _value_is_within_axis_bounds(rmg, 2.9, 0)
    True
    >>> _value_is_within_axis_bounds(rmg, 4.1, 1)
    False
    >>> _value_is_within_axis_bounds(rmg, 3.9, 1)
    True
    """
    axis_coord = rmg.node_axis_coordinates(axis)
    return _value_is_in_bounds(value, (axis_coord[0], axis_coord[-1]))


def is_coord_on_grid(rmg, coords, axes=(0, 1)):
    """Check if coordinates are contained on a grid.

    Parameters
    ----------
    rmg : RasterModelGrid
        Source grid.
    coords : tuple
        Coordinates of point as (x, y)
    axes : tuple, optional
        Check bounds only on a particular axis

    Examples
    --------
    Create a grid that ranges from x=0 to x=4, and y=0 to y=3.

    >>> from landlab import RasterModelGrid
    >>> from landlab.grid.raster_funcs import is_coord_on_grid
    >>> grid = RasterModelGrid(4, 5)
    >>> is_coord_on_grid(grid, (3.999, 2.999))
    True

    Check two points with one call. Numpy broadcasting rules apply for the
    point coordinates.

    >>> is_coord_on_grid(grid, ([3.9, 4.1], 2.9))
    array([ True, False], dtype=bool)

    >>> is_coord_on_grid(grid, ([3.9, 4.1], 2.9), axes=(0, ))
    array([ True,  True], dtype=bool)
    """
    coords = np.broadcast_arrays(*coords)

    is_in_bounds = _value_is_within_axis_bounds(rmg, coords[1 - axes[0]],
                                                axes[0])
    for axis in axes[1:]:
        is_in_bounds &= _value_is_within_axis_bounds(rmg, coords[1 - axis],
                                                     axis)

    return is_in_bounds
