#! /usr/bin/env python


import numpy as np
import itertools


INTERIOR_NODE = 0
FIXED_VALUE_BOUNDARY = 1
FIXED_GRADIENT_BOUNDARY = 2
TRACKS_CELL_BOUNDARY = 3
INACTIVE_BOUNDARY = 4

BAD_INDEX_VALUE = np.iinfo(np.int).max

from landlab.utils import count_repeated_values


def node_count(shape):
    """
    The total number of nodes in a structured grid with dimensions given
    by the tuple, *shape*. Where *shape* is the number of node rows and
    node columns.

    >>> node_count((3, 4))
    12
    """
    assert(len(shape) == 2)
    return shape[0] * shape[1]


def interior_node_count(shape):
    assert(len(shape) == 2)
    return (shape[0] - 2) * (shape[1] - 2)


def cell_count(shape):
    """
    The total number of cells in a structured grid with dimensions, *shape*.
    Where *shape* is a tuple that gives the dimensions of the grid as number
    of rows of nodes followed by number of columns of nodes.

    >>> cell_count((3, 4))
    2
    """
    assert(len(shape) == 2)

    try:
        assert(np.min(shape) > 2)
    except AssertionError:
        return 0
    else:
        return (shape[0] - 2) * (shape[1] - 2)


def active_cell_count(shape):
    """
    Number of active cells. By default, all cells are active so this is
    the same as cell_count.
    """
    return cell_count(shape)


def active_link_count(shape):
    """
    Number of active links in a structured grid with dimensions, *shape*.
    """
    assert(len(shape) == 2)
    return link_count(shape) - 2 * (shape[0] - 1) - 2 * (shape[1] - 1)


def link_count(shape):
    """
    Total (active and inactive) number of links in a structured grid with
    dimensions, *shape*. This is the number of to-links and from-links, not
    the total of the two.

    >>> link_count((3,2))
    7
    """
    assert(len(shape) == 2)
    return shape[1] * (shape[0] - 1) + shape[0] * (shape[1] - 1)


def boundary_cell_count(shape):
    """
    Number of cells that are on the boundary of a structured grid with
    dimensions, *shape*. In fact, cells centered on boundary nodes are not
    really cells. If they were, though, this is how many there would be.

    >>> boundary_cell_count((3, 4))
    10
    """
    assert(len(shape) == 2)
    return 2 * (shape[0] - 2) + 2 * (shape[1] - 2) + 4


def interior_cell_count(shape):
    """
    Number of interior cells. Since cells are only defined on interior nodes,
    this is the same as cell_count.
    """
    return cell_count(shape)


def face_count(shape):
    """
    Total number of faces in a structured grid with dimensions, *shape*. Each
    cell has four faces, and shared faces only count once.

    >>> face_count((3, 4))
    7
    """
    return (shape[0] - 1) * (shape[1] - 2) + (shape[0] - 2) * (shape[1] - 1)


def top_index_iter(shape):
    """
    Iterator for the top boundary indices of a structured grid.
    """
    return xrange(shape[1] * (shape[0] - 1), shape[0] * shape[1])


def bottom_index_iter(shape):
    """
    Iterator for the bottom boundary indices of a structured grid.
    """
    return xrange(0, shape[1])


def left_index_iter(shape):
    """
    Iterator for the left boundary indices of a structured grid.
    """
    return xrange(0, shape[0] * shape[1], shape[1])


def right_index_iter(shape):
    """
    Iterator for the right boundary indices of a structured grid.
    """
    return xrange(shape[1] - 1, shape[0] * shape[1], shape[1])


def left_right_iter(shape, *args):
    """
    Iterator for the left and right boundary indices of a structured grid.
    This iterates over the indices in order rather than iterating all of
    the left boundary and then all of the right boundary.

    >>> import numpy as np
    >>> np.fromiter(left_right_iter((4, 3)), dtype=np.int)
    array([ 0,  2,  3,  5,  6,  8,  9, 11])
    >>> np.fromiter(left_right_iter((4, 3), 2), dtype=np.int)
    array([0, 2, 3, 5])
    >>> np.fromiter(left_right_iter((4, 3), 2, 4), dtype=np.int)
    array([ 6,  8,  9, 11])
    >>> np.fromiter(left_right_iter((4, 3), 1, 4, 2), dtype=np.int)
    array([ 3,  5,  9, 11])
    """
    if len(args) == 0:
        iter_rows = xrange(0, shape[0], 1)
    elif len(args) == 1:
        iter_rows = xrange(0, args[0], 1)
    elif len(args) == 2:
        iter_rows = xrange(args[0], args[1], 1)
    elif len(args) == 3:
        iter_rows = xrange(args[0], args[1], args[2])

    for row in iter_rows:
        yield row * shape[1]
        yield row * shape[1] + shape[1] - 1


def bottom_top_iter(shape):
    """
    Iterates of the bottom indices and then the top indices of a structured
    grid.

    >>> import numpy as np
    >>> np.fromiter(bottom_top_iter((4, 3)), dtype=np.int)
    array([ 0,  1,  2,  9, 10, 11])
    """
    return itertools.chain(bottom_index_iter(shape),
                           top_index_iter(shape))


def boundary_iter(shape):
    """
    Iterates over all of the boundary node indices of a structured grid in
    order.
    """
    return itertools.chain(bottom_index_iter(shape),
                           left_right_iter(shape, 1, shape[0] - 1),
                           top_index_iter(shape))


def boundary_nodes(shape):
    """
    An array of the indices of the boundary nodes.

    >>> boundary_nodes((3, 4))
    array([ 0,  1,  2,  3,  4,  7,  8,  9, 10, 11])
    """
    return np.fromiter(boundary_iter(shape), dtype=np.int)


def bottom_edge_node_ids(shape):
    return np.fromiter(bottom_index_iter(shape), dtype=np.int)


def top_edge_node_ids(shape):
    return np.fromiter(top_index_iter(shape), dtype=np.int)


def left_edge_node_ids(shape):
    return np.fromiter(left_index_iter(shape), dtype=np.int)


def right_edge_node_ids(shape):
    return np.fromiter(right_index_iter(shape), dtype=np.int)


def interior_iter(shape):
    interiors = []
    interiors_per_row = shape[1] - 2
    for row in xrange(shape[1] + 1, shape[1] * (shape[0] - 1), shape[1]):
        interiors.append(xrange(row , row + interiors_per_row))
    return itertools.chain(*interiors)


def interior_nodes(shape):
    return np.fromiter(interior_iter(shape), dtype=np.int)


def node_xyz(shape, *args):
    """
    Get x, y, and z coordinates for nodes in a structured grid with
    dimensions, *shape*.
    """
    assert(len(shape) == 2)

    try:
        spacing = args[0]
    except IndexError:
        spacing = np.ones(len(shape), dtype=np.float)
    else:
        assert(len(spacing) == len(shape))

    try:
        origin = args[1]
    except IndexError:
        origin = np.zeros(len(shape), dtype=np.float)
    else:
        assert(len(origin) == len(origin))

    node_count = np.prod(shape)

    row_y = np.arange(origin[0], shape[0] * spacing[0] + origin[0],
                         spacing[0])
    col_x = np.arange(origin[1], shape[1] * spacing[1] + origin[0],
                         spacing[1])

    (node_x, node_y) = np.meshgrid(col_x, row_y)
    node_z = np.zeros(node_count)

    node_x.shape = (node_count, )
    node_y.shape = (node_count, )

    return (node_x, node_y, node_z)


def active_cells(shape):
    return np.arange(active_cell_count(shape))


def active_cell_node(shape):
    return cell_node_index(shape)


def node_active_cell(shape):
    n_nodes = node_count(shape)

    node_ids = np.empty(n_nodes, dtype=np.int)

    node_ids[boundary_nodes(shape)] = BAD_INDEX_VALUE
    node_ids[interior_nodes(shape)] = np.arange(interior_node_count(shape))

    return node_ids


def cell_node_index(shape):
    node_ids = np.arange(node_count(shape))
    node_ids.shape = shape

    cell_node = node_ids[1:-1, 1:-1].copy()
    cell_node.shape = ((shape[0] - 2) * (shape[1] - 2), )

    return cell_node


def node_link_index(shape):
    node_ids = np.arange(np.prod(shape))
    node_ids.shape = shape

    return (from_node_links(node_ids), to_node_links(node_ids))


def node_tolink_index(shape):
    node_ids = np.arange(np.prod(shape))
    node_ids.shape = shape

    return to_node_links(node_ids)


def node_fromlink_index(shape):
    node_ids = np.arange(np.prod(shape))
    node_ids.shape = shape

    return from_node_links(node_ids)


def to_node_links(node_ids):
    vertical_links = node_ids[1:, :]
    horizontal_links = node_ids[:, 1:]
    return np.concatenate((vertical_links.flat, horizontal_links.flat))


def from_node_links(node_ids):
    vertical_links = node_ids[:-1, :]
    horizontal_links = node_ids[:, :-1]
    return np.concatenate((vertical_links.flat, horizontal_links.flat))


def link_faces(shape, actives=None):
    if actives is None:
        actives = active_links(shape)

    num_links = link_count(shape)

    link_faces = np.empty(num_links, dtype=np.int)
    link_faces.fill(BAD_INDEX_VALUE)
    link_faces[actives] = np.arange(len(actives))

    return link_faces


def node_status(shape, boundary_status=FIXED_VALUE_BOUNDARY):
    """
    The statuses of the nodes in a structured grid with dimensions, *shape*.
    Use the *boundary_status* keyword to specify the status of the top,
    bottom, left and right boundary nodes.
    """
    status = np.empty(np.prod(shape), dtype=np.int8)

    status[interior_nodes(shape)] = INTERIOR_NODE
    status[boundary_nodes(shape)] = boundary_status

    return status


def active_links(shape, node_status_array=None, link_nodes=None):
    """
    >>> active_links((3, 4))
    array([ 1,  2,  5,  6, 11, 12, 13])
    """
    if node_status_array is None:
        node_status_array = node_status(shape)

    if link_nodes is None:
        (link_from_node, link_to_node) = node_link_index(shape)
    else:
        (link_from_node, link_to_node) = link_nodes

    from_node_status = node_status_array[link_from_node]
    to_node_status = node_status_array[link_to_node]

    active_links = (((from_node_status == INTERIOR_NODE) & ~
                     (to_node_status == INACTIVE_BOUNDARY)) |
                    ((to_node_status == INTERIOR_NODE) & ~
                     (from_node_status == INACTIVE_BOUNDARY)))

    (active_links, ) = np.where(active_links)

    return active_links


def setup_inlink_matrix(shape, tonodes=None, return_count=True):
    """
    >>> (link_ids, link_counts) = setup_inlink_matrix((3, 4))
    >>> link_counts  # doctest: +NORMALIZE_WHITESPACE
    array([0, 1, 1, 1,
           1, 2, 2, 2,
           1, 2, 2, 2])
    >>> link_ids[0]  # doctest: +NORMALIZE_WHITESPACE
    array([-1,  8,  9, 10,
            0,  1,  2,  3,
            4,  5,  6,  7])
    >>> link_ids[1]  # doctest: +NORMALIZE_WHITESPACE
    array([-1, -1, -1, -1,
           -1, 11, 12, 13,
           -1, 14, 15, 16])
    """
    num_nodes = node_count(shape)

    node_inlink_matrix = - np.ones((2, num_nodes), dtype=np.int)

    if tonodes is None:
        tonodes = node_tolink_index(shape)

    node_numinlink = np.bincount(tonodes, minlength=num_nodes)
    counts = count_repeated_values(tonodes)
    for (count, (tonodes, link_ids)) in enumerate(counts):
        node_inlink_matrix[count][tonodes] = link_ids

    if return_count:
        return (node_inlink_matrix, node_numinlink)
    else:
        return node_inlink_matrix


def setup_outlink_matrix(shape, fromnodes=None, return_count=True):
    """
    >>> (link_ids, link_counts) = setup_outlink_matrix((3, 4)) 
    >>> link_counts # doctest: +NORMALIZE_WHITESPACE
    array([2, 2, 2, 1,
           2, 2, 2, 1,
           1, 1, 1, 0])
    >>> link_ids[0] # doctest: +NORMALIZE_WHITESPACE
    array([ 0,  1,  2,  3,
            4,  5,  6,  7,
           14, 15, 16, -1])
    >>> link_ids[1] # doctest: +NORMALIZE_WHITESPACE
    array([ 8,  9, 10, -1,
           11, 12, 13, -1,
           -1, -1, -1, -1])
    """
    num_nodes = node_count(shape)

    node_outlink_matrix = - np.ones((2, num_nodes), dtype=np.int)

    if fromnodes is None:
        fromnodes = node_fromlink_index(shape)

    node_numoutlink = np.bincount(fromnodes, minlength=num_nodes)
    counts = count_repeated_values(fromnodes)
    for (count, (fromnodes, link_ids)) in enumerate(counts):
        node_outlink_matrix[count][fromnodes] = link_ids

    if return_count:
        return (node_outlink_matrix, node_numoutlink)
    else:
        return node_outlink_matrix


def node_index_with_halo(shape, halo_indices=BAD_INDEX_VALUE):
    """
    >>> node_index_with_halo((2, 3), halo_indices=-1)
    array([[-1, -1, -1, -1, -1],
           [-1,  0,  1,  2, -1],
           [-1,  3,  4,  5, -1],
           [-1, -1, -1, -1, -1]])
    """
    shape_with_halo = np.array(shape) + 2

    ids = np.empty(shape_with_halo, dtype=np.int)

    (interiors, boundaries) = (interior_nodes(shape_with_halo),
                               boundary_nodes(shape_with_halo)) 

    ids.flat[interiors] = xrange(interior_node_count(shape_with_halo))
    ids.flat[boundaries] = halo_indices

    return ids


def neighbor_array(shape, out_of_bounds=BAD_INDEX_VALUE, contiguous=True):
    """
    >>> neighbors = neighbor_array((2, 3), out_of_bounds=-1)
    >>> neighbors
    array([[-1, -1,  1,  3],
           [ 0, -1,  2,  4],
           [ 1, -1, -1,  5],
           [-1,  0,  4, -1],
           [ 3,  1,  5, -1],
           [ 4,  2, -1, -1]])
    >>> neighbors.flags['C_CONTIGUOUS']
    True
    >>> neighbors = neighbor_array((2, 3), out_of_bounds=-1, contiguous=False)
    >>> neighbors.flags['C_CONTIGUOUS']
    False
    """
    ids = node_index_with_halo(shape, halo_indices=out_of_bounds)

    neighbors = np.vstack((
        ids[1:shape[0] + 1, :shape[1]].flat,
        ids[:shape[0], 1:shape[1] + 1].flat,
        ids[1:shape[0] + 1, 2:].flat,
        ids[2:, 1:shape[1] + 1].flat,
    )).T
    if contiguous:
        return neighbors.copy()
    else:
        return neighbors


def diagonal_array(shape, out_of_bounds=BAD_INDEX_VALUE, contiguous=True):
    """
    Creates a list of IDs of the diagonal cells to each cell, as a 2D array. 
    Only interior cells are assigned neighbors; boundary cells get -1 for
    each neighbor.  The order of the diagonal cells is [topright, topleft,
    bottomleft, bottomright].
    
    NG didn't touch this, but she thinks this should be nodes, not cells.

    >>> diags = diagonal_array((2, 3), out_of_bounds=-1)
    >>> diags
    array([[-1, -1,  4, -1],
           [-1, -1,  5,  3],
           [-1, -1, -1,  4],
           [-1,  1, -1, -1],
           [ 0,  2, -1, -1],
           [ 1, -1, -1, -1]])
    >>> diags.flags['C_CONTIGUOUS']
    True
    >>> diags = diagonal_array((2, 3), out_of_bounds=-1, contiguous=False)
    >>> diags.flags['C_CONTIGUOUS']
    False
    """
    ids = node_index_with_halo(shape, halo_indices=out_of_bounds)

    diags = np.vstack((
        ids[:shape[0], :shape[1]].flat,
        ids[:shape[0], 2:].flat,
        ids[2:, 2:].flat,
        ids[2:, :shape[1]].flat)).T
    if contiguous:
        return diags.copy()
    else:
        return diags


def diagonal_array_slow(shape, out_of_bounds=BAD_INDEX_VALUE):
    (nrows, ncols) = shape
    ncells = shape[0] * shape[1]
    diagonal_cells = - np.ones([ncells, 4], dtype=np.int)
    for r in xrange( 1, nrows-1 ):
        for c in xrange( 1, ncols-1 ):
            cell_id = r * ncols + c
            diagonal_cells[cell_id,2] = cell_id - ncols - 1 # bottom left
            diagonal_cells[cell_id,0] = cell_id + ncols + 1 # top right
            diagonal_cells[cell_id,3] = cell_id - ncols + 1 # bottom right
            diagonal_cells[cell_id,1] = cell_id + ncols - 1 # top left
    return diagonal_cells


def has_boundary_neighbor(neighbors, diagonals,
                          out_of_bounds=BAD_INDEX_VALUE):
    return (out_of_bounds in neighbors |
            out_of_bounds in diagonals)


def has_boundary_neighbor_slow(neighbors, diagonals, out_of_bounds=BAD_INDEX_VALUE):
        #nbr_nodes=self.get_neighbor_list(id)
        #diag_nbrs=self.get_diagonal_list(id)
        
        i=0
        while i < 4 and neighbors[i] != out_of_bounds:
            i += 1
        
        if i < 4:
            return True
        else:
            r = 0
            while r < 4 and diagonals[r] != out_of_bounds:
                r += 1
        
        if r < 4 :
            return True
        else:
            return False


def reshape_array(shape, u, flip_vertically=False, copy=False):
    """
    >>> x = np.arange(12.)
    >>> y = reshape_array((3, 4), x)
    >>> y.shape
    (3, 4)
    >>> y
    array([[  0.,   1.,   2.,   3.],
           [  4.,   5.,   6.,   7.],
           [  8.,   9.,  10.,  11.]])
    >>> y.flags['C_CONTIGUOUS']
    True
    >>> x[0] = -1
    >>> y[0, 0]
    -1.0

    >>> x = np.arange(12.)
    >>> y = reshape_array((3, 4), x, flip_vertically=True)
    >>> y
    array([[  8.,   9.,  10.,  11.],
           [  4.,   5.,   6.,   7.],
           [  0.,   1.,   2.,   3.]])
    >>> y.flags['C_CONTIGUOUS']
    False
    >>> x[0] = -1
    >>> y[-1, 0]
    -1.0
    """
    reshaped_u = u.view()

    try:
        reshaped_u.shape = shape
    except ValueError:
        raise

    if flip_vertically:
        reshaped_u = reshaped_u[::-1, :]

    if copy:
        return reshaped_u.copy()
    else:
        return reshaped_u
