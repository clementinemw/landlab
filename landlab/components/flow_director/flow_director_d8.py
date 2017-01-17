from landlab.components.flow_director.flow_director_to_one import _FlowDirectorToOne
from landlab.components.flow_director import flow_direction_DN
from landlab import FIXED_VALUE_BOUNDARY, FIXED_GRADIENT_BOUNDARY
from landlab import VoronoiDelaunayGrid

import numpy

class FlowDirectorD8(_FlowDirectorToOne):
    """Single-path (steepest direction) flow direction finding on raster grids
     by the D8 method. This method considers flow on all eight links such that
     flow is possible on orthogonal and on diagonal links. 
     
     The method that considers only orthogonal links (D4 method) for raster 
     grids is FlowDirectorSteepest. 

     This method is not implemented for Voroni grids, use 
     FlowDirectorSteepestDescent instead. 

    Stores as ModelGrid fields:
        
        -  Node array of receivers (nodes that receive flow), or ITS OWN ID if
           there is no receiver: *'flow__receiver_node'*
        -  Node array of steepest downhill slopes:
           *'topographic__steepest_slope'*
        -  Node array containing ID of link that leads from each node to its
           receiver, or BAD_INDEX_VALUE if no link:
           *'flow__link_to_receiver_node'*
        -  Boolean node array of all local lows: *'flow__sink_flag'*
        
    The primary method of this class is :func:`run_one_step`.

    Construction::

        FlowDirectorD8(grid, surface='topographic__elevation')

    Parameters
    ----------
    grid : ModelGrid
        A grid of type RasterModelGrid.
    surface : field name at node or array of length node, optional
        The surface to direct flow across, default is field at node: 
        topographic__elevation,.   
  
   
    Examples
    --------
    >>> import numpy as np
    >>> from landlab import RasterModelGrid
    >>> from landlab.components import FlowDirectorD8
    >>> mg = RasterModelGrid((3,3), spacing=(1, 1))
    >>> mg.set_closed_boundaries_at_grid_edges(True, True, True, False)
    >>> _ = mg.add_field('topographic__elevation', 
    ...                  mg.node_x + mg.node_y, 
    ...                  at = 'node')
    >>> fd = FlowDirectorD8(mg, 'topographic__elevation')
    >>> fd.elevs
    array([ 0.,  1.,  2.,  1.,  2.,  3.,  2.,  3.,  4.])
    >>> fd.run_one_step()
    >>> mg.at_node['flow__receiver_node']
    array([0, 1, 2, 3, 0, 5, 6, 7, 8])
    >>> mg.at_node['topographic__steepest_slope']
    array([ 0.        ,  0.        ,  0.        ,  0.        ,  1.41421356,
            0.        ,  0.        ,  0.        ,  0.        ])
    >>> mg.at_node['flow__link_to_receiver_node']
    array([-1, -1, -1, -1, 12, -1, -1, -1, -1])
    >>> mg.at_node['flow__sink_flag']
    array([1, 1, 1, 1, 0, 1, 1, 1, 1], dtype=int8)
    >>> mg_2 = RasterModelGrid((5, 4), spacing=(1, 1))
    >>> elev = np.array([0.,  0.,  0., 0.,
    ...                  0., 21., 10., 0.,
    ...                  0., 31., 20., 0.,
    ...                  0., 32., 30., 0.,
    ...                  0.,  0.,  0., 0.])
    >>> _ = mg_2.add_field('node','topographic__elevation', elev)
    >>> mg_2.set_closed_boundaries_at_grid_edges(True, True, True, False)
    >>> fd_2 = FlowDirectorD8(mg_2)
    >>> fd_2.run_one_step()
    >>> mg_2.at_node['flow__receiver_node'] # doctest: +NORMALIZE_WHITESPACE
    array([  0,  1,  2,  3,
             4,  1,  2,  7,
             8,  6,  6, 11,
            12, 10, 10, 15,
            16, 17, 18, 19])
    
    The flow directors also have the ability to return the flow reciever nodes
    
    >>> receiver = fd.direct_flow()
    >>> receiver 
    array([0, 1, 2, 
           3, 0, 5, 
           6, 7, 8])
    """

    _name = 'FlowDirectorD8'

    def __init__(self, grid, surface='topographic__elevation'):
        self.method = 'D8'
        super(FlowDirectorD8, self).__init__(grid, surface)
        self._is_Voroni = isinstance(self._grid, VoronoiDelaunayGrid)
        if self._is_Voroni:
            raise NotImplementedError('FlowDirectorD8 not implemented for'
                                      'irregular grids, use'
                                      'FlowDirectorSteepest')
            
        self.updated_boundary_conditions()
        
        
    def updated_boundary_conditions(self):
        """
        Call this if boundary conditions on the grid are updated after the
        component is instantiated.
        """
        
        dal, d8t, d8h = self.grid._d8_active_links()
        self._active_links = dal
        self._activelink_tail = d8t
        self._activelink_head = d8h
        
        
    def run_one_step(self):   
        self.direct_flow()
        
        
    def direct_flow(self):
        # step 0. Check and update BCs
        if self._bc_set_code != self.grid.bc_set_code:
            self.updated_boundary_conditions()
            self._bc_set_code = self.grid.bc_set_code           
        
        # step 1. Calculate link slopes. 
        link_slope = - self._grid._calculate_gradients_at_d8_active_links(
                self.elevs)
                
        # Step 2. Find and save base level nodes. 
        (baselevel_nodes, ) = numpy.where(
            numpy.logical_or(self._grid.status_at_node == FIXED_VALUE_BOUNDARY,
                             self._grid.status_at_node == FIXED_GRADIENT_BOUNDARY))
                   
        # Calculate flow directions by D8 method       
        receiver, steepest_slope, sink, recvr_link = \
        flow_direction_DN.flow_directions(self.elevs, self._active_links,
                                     self._activelink_tail,
                                     self._activelink_head, link_slope,
                                     grid=self._grid,
                                     baselevel_nodes=baselevel_nodes)
        self.sink = sink
        
       # Save the four ouputs of this component.                                  
        self._grid['node']['flow__receiver_node'][:] = receiver
        self._grid['node']['topographic__steepest_slope'][:] = steepest_slope
        self._grid['node']['flow__link_to_receiver_node'][:] = recvr_link
        self._grid['node']['flow__sink_flag'][:] = numpy.zeros_like(receiver,
                                                                    dtype=bool)
        self._grid['node']['flow__sink_flag'][sink] = True
    
        return receiver
        
        
if __name__ == '__main__':
    import doctest
    doctest.testmod()