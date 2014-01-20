# This program calculates the dn2t of the deltaN2.nc file given and then
# if not already done, computes the vertical displacement amplitude and creates an entry for it in
# the database "/Volumes/HD4/vertical_displacement_amplitude/%d/a_xi.nc 
# The deltaN2 database and the vertical_displacement_amplitude database are
# related by the deltaN2_id fields.
#


import playncfile
import matplotlib
import argparse 
import numpy
import labdb
import os
import netCDF4
import pylab
import matplotlib.pyplot as plt
import Energy_flux


def createncfile(dz_id,t,x,z,
        a_xi_id = None
        ):
    """ 
    create the nc file in which we will store a_xi array.
    create a row in the database for the nc file stored
    update the database

    Axi_id will be chosen as the next available id if a_xi_id is None.
    """
    print "inside createncfile function"
    db = labdb.LabDB()
    #create the directory in which to store the nc file
    if a_xi_id is None:
        sql = """INSERT into vertical_displacement_amplitude (dz_id) VALUES (%d)"""%(dz_id)  
        print sql
        db.execute(sql)
        sql = """SELECT LAST_INSERT_ID()""" 
        rows = db.execute(sql)
        a_xi_id = rows[0][0]
    else:
        sql = "SELECT dz_id FROM vertical_displacement_amplitude WHERE a_xi_id = %s" % a_xi_id
        previous_dz_id, = db.execute_one(sql)
        if previous_dz_id != dz_id:
            print "dz_id, a_xi_id mismatch!"
            return None

    a_xi_path = "/Volumes/HD4/vertical_displacement_amplitude/%d" % a_xi_id 
    if not os.path.exists(a_xi_path):
        os.mkdir(a_xi_path)

    a_xi_filename = os.path.join(a_xi_path,"a_xi.nc")
    print "A xi : ",a_xi_filename


    # Declare the nc file for the first time
    nc = netCDF4.Dataset(a_xi_filename,'w',format = 'NETCDF4')
    row_dim = nc.createDimension('row',964)
    col_dim = nc.createDimension('column',1292)
    lenT=t.shape[0]  #lenT is the length of the dz file
    
    # changing time to underfined as the variable is set to being contiguous
    # despite setting contiguous=False which is also the default setting
    #print "time axis  length",lenT     # debug info
    #t_dim = nc.createDimension('time',lenT)
    t_dim = nc.createDimension('time', None)

    # Dimensions are also variable
    ROW = nc.createVariable('row',numpy.float32,('row'),contiguous=False)
    print  nc.dimensions.keys(), ROW.shape,ROW.dtype
    COLUMN = nc.createVariable('column',numpy.float32,('column'),contiguous=False)
    print nc.dimensions.keys() , COLUMN.shape, COLUMN.dtype
    TIME = nc.createVariable('time',numpy.float32,('time'),contiguous=False)
    print nc.dimensions.keys() ,TIME.shape, TIME.dtype

    # declare the 3D data variable 
    a_xi = nc.createVariable('a_xi_array',numpy.float32,('time','row','column'),
            contiguous=False)
    print nc.dimensions.keys() ,a_xi.shape,a_xi.dtype

    # assign the values
    
    #TIME[:] = t[:]
    ROW[:] = z
    COLUMN[:] = x

    nc.close()
    db.commit()
    return a_xi_id,a_xi_filename


def append2ncfile(a_xi,var,num):
    """
    Append the array to the end of the nc file
    """
    print "appending.."
    a_xi[num] = var

    
def compute_a_xi(dz_id, cache=True):
    """
        Given an dz_id, compute the vertical displacement Axi
    """
    # access database
    db = labdb.LabDB()

    #check if the dataset already exists
    sql = """SELECT a_xi_id FROM vertical_displacement_amplitude WHERE\
             dz_id = %d""" % (dz_id)
    rows = db.execute(sql)

    a_xi_id = None
    if len(rows) > 0:
    
        # A xi array already computed
        a_xi_id = rows[0][0]

        a_xi_path = "/Volumes/HD4/vertical_displacement_amplitude/%d/" % a_xi_id
        a_xi_filename = a_xi_path + 'a_xi.nc'

        if os.path.exists(a_xi_filename) and cache:
            return ax_id
        else:
            # delete ax_xi.nc if it exists and recreate
            if os.path.exists(a_xi_filename):
                os.unlink(a_xi_filename)

    #  open the dataset dz.nc for calculating a_xi
    filepath = "/Volumes/HD4/dz/%d/dz.nc"  % dz_id
    if not os.path.exists(filepath):
        print filepath, "not found"
        return
    nc = netCDF4.Dataset(filepath,'a')
    
    # loading the dz data from the nc file
    dz = nc.variables['dz_array']
    t = nc.variables['time']
    print "t from dz_array", t[:]
    z = nc.variables['row']
    x = nc.variables['column']
    # print information about dz dataset
    print "variables  of the nc file :", nc.variables.keys()
    print "dz shape : " , dz.shape
    print "t  shape : " , t.shape
    print "z shape : " , z.shape
    print "x shape : " , x.shape
    
    # call get_info function from Energy_flux program :: to get info!
    
    sql = """ SELECT expt_id  FROM dz WHERE dz_id = %d """ % dz_id
    rows = db.execute(sql)
    expt_id = rows[0][0]

    vid_id, N, omega,kz,theta = Energy_flux.get_info(expt_id)

    print "V_ID:",  vid_id,"\n N:", N, "\n OMEGA: ", omega,"\n kz:",kz,"\n theta : ", theta
    # calculate dt
    dt = numpy.mean(numpy.diff(t))
    print "dt of dz:",dt
    
    #call the function to create the nc file in which we are going to store the dz array
    a_xi_id,a_xi_filename = createncfile(dz_id,t,x,z,a_xi_id=a_xi_id)
    
    #get info about the nc file to see if the var is contiguous
    print " info axi nc file :  chk if the var is contiguous"
    os.system('ncdump -h -s %s' % a_xi_filename)
    
    # open the a_xi nc file for appending data
    axi_nc=netCDF4.Dataset(a_xi_filename,'a')
    a_xi = axi_nc.variables['a_xi_array']
    # setting the time axis
    axi_time = axi_nc.variables['time']
    axi_time[:] = t[:]

    # Calculate kx 
    rho0 = 0.998
    kx = (omega * kz)/(N*N - omega*omega)**0.5
    const1 = -1.0 * omega* N * N * kz
    print "constant1 :" ,const1
    
    # calculate constants needed for getting dn2t from dz
    
    sql = """SELECT length FROM video WHERE video_id = %d  """ % vid_id
    rows = db.execute(sql)
    win_l = rows[0][0]
    win_l=win_l*1.0
    print "length" , win_l
    n_water = 1.3330
    L_tank = 453.0
    gamma = 0.0001878
    const2 = -1.0/(gamma*((0.5*L_tank*L_tank)+(L_tank*win_l*n_water)))
    print "constant2:",const2


    for num in range(dz.shape[0]):
        var1 = (1.0*const2*dz[num,:,:])/(dt*const1)
        print "appending frame %d" % num
        append2ncfile(a_xi,var1,num)
    print "done...!"

    axi_nc.close()
    nc.close()
    return a_xi_id

def test():
    nc = netCDF4.Dataset('/Volumes/HD4/dn2t/3/dn2t.nc','r')
    dn2t = nc.variables['dn2t_array']
    Eflux1 = dn2t[:,200,:]*4.125
    t = nc.variables['time']
    x = nc.variables['column']
    z = nc.variables['row']
    
    Eflux1 = numpy.ma.masked_array(Eflux1,Eflux1 < 0.05)
    Eflux1 = numpy.ma.masked_array(Eflux1,Eflux1 < -0.05)
    
    plt.figure()
    plt.subplot(1,4,1)
    plt.imshow(Eflux1.T,extent=[x[0],x[-1],t[0],t[-1]],vmin=-.20,vmax=0.20, interpolation = 'nearest', aspect = 'auto')
    plt.colorbar()
    plt.xlabel('length')
    plt.ylabel('time')
    plt.title('time series energy flux (single row)')
    Eflux2= dn2t[:,:,700] * 4.125
    Eflux2 = numpy.ma.masked_array(Eflux2,Eflux2 < 2.0) 
    Eflux21= dn2t[:,:,100] * 4.125
    Eflux21 = numpy.ma.masked_array(Eflux21,Eflux21 < 2.0)
    Eflux22= dn2t[:,:,300] * 4.125
    Eflux22 = numpy.ma.masked_array(Eflux22,Eflux22 < 2.0) 
    Eflux23= dn2t[:,:,500] * 4.125
    Eflux23 = numpy.ma.masked_array(Eflux23,Eflux23 < 2.0) 
    Eflux24= dn2t[:,:,900] * 4.125
    Eflux24 = numpy.ma.masked_array(Eflux24,Eflux24 < 2.0) 
    Eflux25= dn2t[:,:,1100] * 4.125
    Eflux25 = numpy.ma.masked_array(Eflux25,Eflux25 < 2.0) 
    

    plt.subplot(1,4,2)
    plt.imshow(Eflux2,extent=[t[0],t[-1],z[0],z[-1]],vmin=-.50,vmax=0.50, interpolation = 'nearest', aspect = 'auto')
    plt.colorbar()
    plt.xlabel('time')
    plt.ylabel('depth')
    plt.title(' time series energy flux (single column)')
    Eflux3= dn2t[400,:,:] * 4.125
    plt.subplot(1,4,3)
    plt.imshow(Eflux3.T,extent=[x[0],x[-1],z[0],z[-1]],vmin=-.50,vmax=0.50, interpolation = 'nearest', aspect = 'auto')
    plt.colorbar()
    plt.xlabel('length')
    plt.ylabel('depth')
    plt.title('energy flux - single instant in time ')
    plt.subplot(1,4,4)
    plt.plot(t[:],numpy.mean(Eflux2,1),t[:],numpy.mean(Eflux21,1),t[:],numpy.mean(Eflux22,1),t[:],numpy.mean(Eflux24,1),t[:],numpy.mean(Eflux25,1))
    plt.xlabel('length')
    plt.ylabel('depth')
    plt.title('columnwise averaged  energy flux ')



    plt.show()

def UI():
    """
    take the dz_id from the user and calculate the change in the squared
    buoyancy frequency (deltaN2), the time derivative of the deltaN2, U, W, and
    the energy flux
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("dz_id", type=int, help="Enter the dz_id")
    args = parser.parse_args()
    a_xi_id = compute_a_xi(args.dz_id)
    print a_xi_id

if __name__ == "__main__":
    #test()
    UI()
