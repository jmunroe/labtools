"""
Routines for computing Fourier transforms of f(x,z,t) fields

(could be generalized later so that f(x1, x2, .., xn) 
     and variable number of axes are given)
Computes the Hilbert transform and saves the filtered data into right.nc and
left.nc files

"""
import operator
import os
import numpy as np
import matplotlib.pyplot as plt
import argparse
import netCDF4
import pylab
import copy
import labdb


def create_nc_file(a_xi_id):

    """ Need to compute HT for the first time.
        Need to create the path for the right and left wave fields and create the empty nc file
    """
    
    db = labdb.LabDB()
    # Get experiment ID
    
    sql = """ SELECT dz.video_id, dz.expt_id FROM dz INNER JOIN \
            vertical_displacement_amplitude ON (dz.dz_id = \
            vertical_displacement_amplitude.dz_id AND \
            vertical_displacement_amplitude.a_xi_id = %d) """ %a_xi_id
    rows = db.execute(sql)
    print rows 
    video_id = rows[0][0]
    expt_id = rows[0][1]
    print " experiment ID : ", expt_id, "Video ID :", video_id
    
    # get the window length and window height
    sql = """SELECT length FROM video WHERE video_id = %d  """ % video_id
    rows = db.execute(sql)
    win_l = rows[0][0]*1.0
    
    sql = """SELECT height FROM video WHERE video_id = %d  """ % video_id
    rows = db.execute(sql)
    win_h = rows[0][0]*1.0

    # Create the directory in which to store the nc file
    sql = """INSERT INTO filtered_waves (a_xi_id,video_id)\
            VALUES (%d,%d)""" % (a_xi_id,video_id)
    print sql
    db.execute(sql)
    sql = """SELECT LAST_INSERT_ID()"""
    rows = db.execute(sql)
    fw_id = rows[0][0]
    fw_path = "/Volumes/HD4/filtered_waves/%d" % fw_id
    os.mkdir(fw_path)
    fw_filename = os.path.join(fw_path, "waves.nc")
    
    # Declare the nc file for the first time 
        
    nc = netCDF4.Dataset(fw_filename,'w',format = 'NETCDF4')
    row_dim = nc.createDimension('row',None)
    col_dim = nc.createDimension('column',1292/2)
    t_dim = nc.createDimension('time',None)
    
    #the dimensions are also variables
    ROW = nc.createVariable('row',np.float32,('row'))
    print  nc.dimensions.keys(), ROW.shape,ROW.dtype
    COLUMN = nc.createVariable('column',np.float32,('column'))
    print nc.dimensions.keys() , COLUMN.shape, COLUMN.dtype
    TIME = nc.createVariable('time',np.float32,('time'))
    print nc.dimensions.keys() ,TIME.shape, TIME.dtype
    
    # declare the 3D data variable 
    raw = nc.createVariable('raw_array',np.float32,('row','time','column'))
    left_w = nc.createVariable('left_array',np.float32,('row','time','column'))
    right_w = nc.createVariable('right_array',np.float32,('row','time','column'))
    print nc.dimensions.keys() 
    print "L", left_w.shape,left_w.dtype
    print "R", right_w.shape,right_w.dtype
    
    # the length and height dimensions are variables containing the length and
    # height of each pixel in cm
    C =np.arange(0,win_l,win_l*2/1292,dtype=float)
    COLUMN[:] = C

    db.commit()
    nc.close()
    return fw_filename,fw_id


#def task_hilbert_func(a_xi_id,t_start,t_end,r_start,r_end,c_start,c_end,t_step,r_step,c_step,maxmin):
def task_hilbert_func(a_xi_id,maxmin,plotcolumn):
    db = labdb.LabDB()
    
    #check if the file already exists
    sql = """ SELECT fw_id FROM filtered_waves WHERE a_xi_id = %d""" %a_xi_id
    rows=db.execute(sql)
    if len(rows)>0:
        print "It has already been computed"
        fw_path = "/Volumes/HD4/filtered_waves/%d/waves.nc" % rows[0][0]
        print fw_path
        #just_plot(fw_path,a_xi_id,maxmin,plotcolumn)
        #plt.show()
        return
    # create the nc file for the first time for storing the filtered data
    fw_filename,fw_id = create_nc_file(a_xi_id)

    #set the path to the data
    path = "/Volumes/HD4/vertical_displacement_amplitude/%d" % a_xi_id
    filename = path+ "/a_xi.nc"
    
    # check for existance of axi_nc
    if not os.path.exists(filename):
        print "Error: axi_nc", filename, "not found"
        raise


    axi_nc = netCDF4.Dataset(filename, 'r')
    
    #a,b,c,d,e,f=t_start,t_end,r_start,r_end,c_start,c_end
     
    # variables
    t = axi_nc.variables['time'][::2]
    z = axi_nc.variables['row'][:]
    x = axi_nc.variables['column'][::2]

    # DEBUG MESSAGES
    print "x shape",x.shape
    print "z shape",z.shape
    print "t shape",t.shape
    
    # determine lengths of x, z, t
    nz = len(z)
    nx = len(x)
    nt = len(t)
    print "length of X, T, Z:  ",nx,nt,nz

    # assume data is sampled evenly
    dx = np.mean(np.diff(x))
    dt = np.mean(np.diff(t))
    dz = np.mean(np.diff(z))
    print "dx,dz,dt :: " ,dx,dz,dt

    # determine frequency axes
    kx = np.fft.fftfreq(nx, dx)
    kx = np.fft.fftshift(kx)
    
    omega = np.fft.fftfreq(nt, dt)
    omega = np.fft.fftshift(omega)
    
    print "kx shape: ", kx.shape
    print "omega shape: ", omega.shape
    
    # create a 2D mesh grid so that omega,kx and fft have the same dimensions
    K,O=np.meshgrid(kx,omega[::-1])
    print "KX.shape" ,K.shape
    print "OMEGA.shape",O.shape
    
    # Open the nc file for writing data
    nc = netCDF4.Dataset(fw_filename,'a')
    raw = nc.variables['raw_array']
    left = nc.variables['left_array']
    right = nc.variables['right_array']
    ft = nc.variables['time']
    fx = nc.variables['column']
    fz = nc.variables['row']
    # data stored into the nc file
    ft[:] = np.mgrid[t[0]:t[-1]:nt *1.0j]
    
    # print information about dz dataset
    print "variables  of the nc file :", nc.variables.keys()
    print "left_w shape : " , left.shape
    print "right_w shape : " , right.shape
    print "t  shape : " , ft.shape
    print "x  shape : " , fx.shape
    print "z  shape : " , fz.shape


    for count in range(nz):
        print "calculating 2DFFT and performing HT for row %d out of %d..." %(count,nz)
        a_xi_arr = axi_nc.variables['a_xi_array'][::2,count,::2]
        print a_xi_arr.shape
        # FFT the data and Normalize and shift so that zero frequency is at the center
        F = np.fft.fftshift(np.fft.fft2(a_xi_arr,axes=(0,1)))
        print "## Completed: FFT"
        Fright,Fleft = np.copy(F),np.copy(F)
        Fright[operator.or_(operator.and_(O > 0.0,K < 0.0),operator.and_(O<0.0,K>0.0))] = 0.0
        Fleft[operator.or_(operator.and_(O > 0.0,K > 0.0),operator.and_(O<0.0,K<0.0))] = 0.0
        print "## Completed HT"
        
        # inverse shift and ifft the fft-ed data to get back the rightward
        # travelling and leftward travelling axi
        a_xi_R = np.fft.ifft2(np.fft.ifftshift(Fright),axes=(1,0))
        a_xi_L = np.fft.ifft2(np.fft.ifftshift(Fleft),axes=(1,0))
        print "a_xi .shape", a_xi_L.shape
        
        raw[count,:,:]= np.reshape(a_xi_arr,(1,a_xi_arr.shape[0],a_xi_arr.shape[1]))
        right[count,:,:] = np.reshape(np.real(a_xi_R),(1,a_xi_arr.shape[0],a_xi_arr.shape[1]))
        left[count,:,:] = np.reshape(np.real(a_xi_L),(1,a_xi_arr.shape[0],a_xi_arr.shape[1]))
        
 
    fz[:]= np.mgrid[z[0]:z[-1]:nz*1.0j]
    print "ft.shape",ft.shape
    print ft[0],ft[-1]
    print "fz.shape",fz.shape
    print fz[0],fz[-1]
    print "fx.shape",fx.shape
    print fx[0],fx[-1]

    print "@@@ stored the data into nc file @@@"
    nc.close()
    axi_nc.close()
    return
    
    """
    #generate a unique path for storing plots
    import datetime as dt
    now = dt.datetime.now()
    print now
    path = "/Users/prajvala/Desktop/figures/axi_LR/axi%d_%d-%d-%d_%d-%d-%d/" %\
            (a_xi_id,now.day,now.month,now.year,now.hour,now.minute,now.second)
    os.mkdir(path)
    fname1 =os.path.join(path,"plot1.pdf")
    fname2=os.path.join(path,"plot2.pdf")
    names= [fname1,fname2]

    print names

    #call the plotting function
    #column = 500
    plot_axes=np.array([ft,fz,fx])
    print plot_axes.shape

    print raw.shape
    print plot_axes.shape
    plot_plots(raw[:,:,plotcolumn],right[:,:,plotcolumn],left[:,:,plotcolumn],plotcolumn,plot_axes,maxmin,names)

    nc.close()
    plt.show()
    """

def just_plot(fw_path,a_xi_id,maxmin,plotcolumn):
    
    # Open the nc file for reading data
    nc = netCDF4.Dataset(fw_path,'r')
    raw = nc.variables['raw_array']
    left = nc.variables['left_array']
    right = nc.variables['right_array']
    ft = nc.variables['time']
    fz = nc.variables['row']
    fx = nc.variables['column']
    # print information about dz dataset
    print "variables  of the nc file :", nc.variables.keys()
    print "left_w shape : " , left.shape
    print "right_w shape : " , right.shape
    print "t  shape : " , ft.shape

    #generate a unique path for storing plots
    import datetime as dt
    now = dt.datetime.now()
    print now
    path = "/Users/prajvala/Desktop/figures/axi_LR/axi%d_%d-%d-%d_%d-%d-%d/" %\
            (a_xi_id,now.day,now.month,now.year,now.hour,now.minute,now.second)
    os.mkdir(path)
    fname1 =os.path.join(path,"plot1.pdf")
    fname2=os.path.join(path,"plot2.pdf")
    names= [fname1,fname2]

    print names

    #call the plotting function
    plot_axes=np.array([ft,fz,fx])

    print plot_axes.shape
    plot_plots(raw[:,:,plotcolumn],right[:,:,plotcolumn],left[:,:,plotcolumn],plotcolumn,plot_axes,maxmin,names)

    nc.close()
    plt.show()


def plot_plots(var1,var2,var3,col,plotaxes,maxmin,name):
    t = plotaxes[0]
    z = plotaxes[1]
    x = plotaxes[2]
    print x.shape
    print var1.shape
    print x[col]
    
    print "x", x[0],x[-1]
    print "z", z[0],z[-1]
    print "t", t[0],t[-1]

    fig = plt.figure(1,figsize=(17,13))
    fig.patch.set_facecolor('white')
    
    a,b = 0,-1
    ax1 = plt.subplot(3,1,1)
    plt.imshow(var1[a:b,:],extent=[t[0],t[-1],z[b],z[a]],vmin=-maxmin,vmax=maxmin,\
            aspect = 'auto', interpolation = 'nearest')
    plt.title('Timeseries of Vertical Displacement Amplitude (cm) \n \
            Data (before applying HT ) %dcm from the wavegenerator' % (90+x[col]))
    plt.ylabel('depth (cm)')
    plt.colorbar()
    
    plt.subplot(3,1,2,sharex = ax1,sharey=ax1)
    plt.imshow(var2[a:b,:],extent=[t[0],t[-1],z[b],z[a]],vmin=-maxmin,vmax=maxmin,\
            aspect = 'auto', interpolation = 'nearest')
    plt.title('(Data after applying HT) Rightward ')
    plt.ylabel('depth (cm)')
    plt.colorbar()
    pylab.subplot(3,1,3,sharex=ax1,sharey=ax1)
    plt.imshow(var3[a:b,:],extent=[t[0],t[-1],z[b],z[a]],vmin=-maxmin,vmax=maxmin,\
            aspect='auto', interpolation = 'nearest')
    plt.title('Leftward')
    plt.ylabel('depth (cm)')
    plt.xlabel('time (s)')
    plt.colorbar()
    plt.savefig(name[1],facecolor = 'w',edgecolor= 'b',format='pdf',transparent=False)
    plt.figure(2,figsize=(15,10))
    plt.imshow(var1[a:b,:],extent=[t[0],t[-1],z[b],z[a]],vmin=-maxmin,vmax=maxmin,\
            aspect = 'auto', interpolation = 'nearest')
    plt.title('Timeseries of Vertical Displacement Amplitude (cm) \n \
        Data (before applying HT ) %dcm from the wavegenerator' % (90+x[col]))
    plt.ylabel('depth (cm)')
    plt.xlabel('time (s)')
    plt.colorbar()
    return

def hilbert_func(a_xi_id,t_start,t_end,r_start,r_end,c_start,c_end,t_step,r_step,c_step,maxmin):
    db= labdb.LabDB()
    # get the path to the nc file
    # Open &  Load the nc file
    path = "/Volumes/HD4/vertical_displacement_amplitude/%d" % a_xi_id
    filename = path+ "/a_xi.nc"
    nc = netCDF4.Dataset(filename)
    #load the variables
    print "loading giant array ...."
    a,b,c,d,e,f=t_start,t_end,r_start,r_end,c_start,c_end
    a_xi_arr = nc.variables['a_xi_array'][a:b:t_step,c:d:r_step,e:f:c_step]
    print "data is in memory!"

    t = nc.variables['time'][a:b:t_step]
    z = nc.variables['row'][c:d:r_step]
    x = nc.variables['column'][e:f:c_step]
    
    print "data:: ", a_xi_arr.shape
    print "x shape",x.shape
    print "z shape",z.shape
    print "t shape",t.shape
    
    # get experiment ID
    sql = """select expt_id from dz where dz_id = (select dz_id from dn2t where\
            id= (select dn2t_id from vertical_displacement_amplitude where a_xi_id=%d))""" % a_xi_id
    rows = db.execute(sql)
    expt_id = rows[0][0]
    print "expt ID: " ,expt_id

    # Select region of interest and convert all the variables into float16 to
    # save memory
    print "convert to float 16 and save memory..."
    a_xi_arr = np.float16(a_xi_arr)
    x = np.float16(x)
    z = np.float16(z)
    t = np.float16(t)

    # determine lengths of x, z, t
    nz = len(z)
    nx = len(x)
    nt = len(t)
    print "length of X, T:  ",nx,nt

    # assume data is sampled evenly
    dx = np.mean(np.diff(x))
    dt = np.mean(np.diff(t))
    print "dx,dt :: " ,dx,dt
    
    # perform FFT along 2 dimensions ..x and t
    # Normalize and shift so that zero frequency is at the center
    print "calculating 2DFFT..."
    a_xi_fft = np.fft.fft2(a_xi_arr,axes=(0,2)) 
    F = np.fft.fftshift(a_xi_fft)
    print "done.", F.shape
    
    # determine frequency axes
    kx = np.fft.fftfreq(nx, dx)
    kx = np.fft.fftshift(kx)
    
    omega = np.fft.fftfreq(nt, dt)
    omega = np.fft.fftshift(omega)
    
    print "kx shape: ", kx.shape
    print "omega shape: ", omega.shape
    
    # create a 2D mesh grid so that omega,kx and fft have the same dimensions
    K,O=np.meshgrid(kx,omega[::-1])
    print "KX.shape" ,K.shape
    print "OMEGA.shape",O.shape
    
    #calling the filter to separate out the waves travelling right from those
    #travelling left
    count,end = 0,F.shape[1]-1
    
    F_L = np.zeros((nt,nz,nx)).astype(complex)*1.0
    F_R = np.zeros((nt,nz,nx)).astype(complex)*1.0
    
    print F.shape,F_R.shape,F_L.shape
    while (count<=end):
        print "done with %d out of %d" % (count,end)
        F_R[:,count,:], F_L[:,count,:]= filter_LR(K,O,F[:,count,:])
        count+=1
       
    print "shape of F_R and F_L" , F_R.shape ,"and ", F_L.shape
    
    # inverse shift and ifft the fft-ed data to get back the rightward
    # travelling and leftward travelling deltaN2
    F_Rinvs = np.fft.ifftshift(F_R)
    a_xi_R = np.fft.ifft2(F_Rinvs,axes=(2,0))
    print "a_xi_R.shape", a_xi_R.shape
    F_Linvs = np.fft.ifftshift(F_L)
    a_xi_L = np.fft.ifft2(F_Linvs,axes=(2,0))
    print "a_xi_L.shape", a_xi_L.shape
    #maxmin = 0.04
    
    # call the function that computes the running mean
    # get the time period of the wave
    sql = """ SELECT frequency_measured FROM wavemaker WHERE wavemaker_id \
            = (SELECT wavemaker_id FROM wavemaker_experiments WHERE \
            expt_id = %d) """ % expt_id
    rows = db.execute(sql)
    t_period = 1.0/ rows[0][0]
    print "time period of the wave : %f s" %t_period
    
    window =  t_period /dt 
    window = np.int16(window)
    print "window : ", window
    
    #R_avg = moving_average(a_xi_R[:,:,100],window)

    #L_avg = moving_average(a_xi_L[:,:,100],window)
    path = "/Users/prajvala/Desktop/figures/axi_LR/%d/" % a_xi_id
    os.mkdir(path)
    
    fname1 = os.path.join(path,"time%f-%f_L%f-%f_H%f-%f_maxmin%f_plot1.pdf"\
            %(t[0],t[-1],x[0],x[-1],z[0],z[-1],maxmin))
    print fname1
    fname2 = os.path.join(path,"time%f-%f_L%f-%f_H%f-%f_maxmin%f_plot2.pdf"\
            %(t[0],t[-1],x[0],x[-1],z[0],z[-1],maxmin))
    fname3 = os.path.join(path,"time%f-%f_L%f-%f_H%f-%f_maxmin%f_plot3.pdf"\
            %(t[0],t[-1],x[0],x[-1],z[0],z[-1],maxmin))


def moving_average(arr,window):
    n_rows = arr.shape[1]
    avg=[]
    for nr in range(n_rows):
        print nr,"out of ",n_rows
        temp = arr[:,nr]
        sum=[]
        for i in range(window):
            sum.append(np.pad(temp[i:], (0,i),'constant',constant_values=(0,)))
        temp1= np.sum(sum,0)/window
        avg.append(temp1[:-(window-1)])
    avg = np.float32(avg)
    avg = np.array(avg)
    print "average shape: ", avg.shape
    return avg


def filter_LR(K,O,F):
    Fright,Fleft = np.copy(F),np.copy(F)
    Fright[operator.or_(operator.and_(O > 0.0,K < 0.0),operator.and_(O<0.0,K>0.0))] = 0.0
    Fleft[operator.or_(operator.and_(O > 0.0,K > 0.0),operator.and_(O<0.0,K<0.0))] = 0.0
    print "@@@@"
    return Fright,Fleft

def f1ilter_LR(K,O,F):
    Fright,Fleft = np.copy(F),np.copy(F)
    Fright[  O < 0.0 ] = 0.0
    Fleft[  O < 0.0 ] = 0.0
    Fleft,Fright = Fleft * 2.0 , Fright*2.0
    Fright[ K < 0.0 ] = 0.0
    Fleft[ K > 0.0]  = 0.0
    return Fright,Fleft

def xzt_fft(a_xi_id,row_z,col_start,col_end,max_min):
    """
    Given the three-dimensional array f(x,z,t) gridded onto x, z, t
    compute the Fourier transform F.

    Returns F, X, Z, T where F is the Fourier transform and 
    X, Z, T are the frequency axes
    """

    # get the path to the nc file
    # Open &  Load the nc file
    path = "/Volumes/HD4/vertical_displacement_amplitude/%d" % a_xi_id
    filename = path+ "/a_xi.nc"
    nc = netCDF4.Dataset(filename)
    
    #load the variables
    a_xi_arr = nc.variables['a_xi_array']
    t = nc.variables['time']
    x = nc.variables['column'][col_start:col_end]
    z = nc.variables['row']

    # Select region of interest and convert all the variables into float16 to
    # save memory
    a_xi_arr = a_xi_arr[:,row_z,col_start:col_end]
    #a_xi_arr = a_xi_arr - a_xi_arr.mean()
    print "mean.shape :: ",a_xi_arr.mean().shape

    a_xi_arr = np.float16(a_xi_arr)
    x = np.float16(x)
    t = np.float16(t)
    #z = np.float16(z)


    print "Vertical Displacement Amplitude array shape: " ,a_xi_arr.shape
    print "T shape: " ,t.shape
    print "X shape: " ,x.shape
    print "Z shape: " ,z.shape

    # determine lengths of x, z, t
    #nz = len(z)
    nx = len(x)
    nt = len(t)
    print "length of X, T:  ",nx,nt

    # assume data is sampled evenly
    #dz = z[1] - z[0]
    dx = np.mean(np.diff(x))
    dt = np.mean(np.diff(t))
    print "dx,dt :: " ,dx,dt
    
    # perform FFT alone all three dimensions
    # Normalize and shift so that zero frequency is at the center
    a_xi_fft = np.fft.fft2(a_xi_arr) 
    F = np.fft.fftshift(a_xi_fft)
    
    
    F_invs = np.fft.ifftshift(F)
    a_xi_rec = np.fft.ifft2(F_invs)

    print "fft of deltaN2 _array:: type and size::", a_xi_fft.dtype, a_xi_fft.size
    print "shape:", a_xi_fft.shape
    #print"F: ", F[10,200]
    #print "abs F:", abs(F[10,200])
    #print "F.real",F[10,200].real
    #print "F.imag", F[10,200].imag
    
    # determine frequency axes
    #kz = np.fft.fftfreq(nz, dz)
    #kz = 2*np.pi*np.fft.fftshift(kz)
    kx = np.fft.fftfreq(nx, dx)
    kx = np.fft.fftshift(kx)
    
    omega = np.fft.fftfreq(nt, dt)
    omega = np.fft.fftshift(omega)
    
    print "kx shape: ", kx.shape
    #print "kz shape: ", kz.shape
    print "omega shape: ", omega.shape
    print "omega",omega
    # create a 2D mesh grid so that omega,kx and fft have the same dimensions
    K,O=np.meshgrid(kx,omega[::-1])
    print "KX.shape" ,K.shape
    print "OMEGA.shape",O.shape
    
    #calling the filter to separate out the waves travelling right from those
    #travelling left
    F_R, F_L = filter_LR(K,O,F)
    print "shape of F_R and F_L" , F_R.shape ,"and ", F_L.shape

    # inverse shift and ifft the fft-ed data to get back the rightward
    # travelling and leftward travelling deltaN2
    F_Rinvs = np.fft.ifftshift(F_R)
    a_xi_R = np.fft.ifft2(F_Rinvs)
    print "a_xi_R.shape", a_xi_R.shape
    F_Linvs = np.fft.ifftshift(F_L)
    a_xi_L = np.fft.ifft2(F_Linvs)
    print "a_xi_L.shape", a_xi_L.shape

    plt.figure(8)
    pylab.subplot(2,1,1)
    plt.imshow(a_xi_arr,vmin=-max_min,vmax=max_min,\
            aspect = 'auto', interpolation = 'nearest')
    plt.xlabel('raw data at depth at %d cm' % z[row_z])
    plt.colorbar()
    pylab.subplot(2,1,2)
    plt.imshow(a_xi_rec.real,extent=[x[0],x[-1],t[-1],t[0]],vmin=-max_min,vmax=max_min,\
            aspect = 'auto', interpolation = 'nearest')
    plt.xlabel('reconstructed data (directly from raw data) for sanity check at depth %d cm' % z[row_z])
    plt.colorbar()
    
    plt.figure(1)
    pylab.subplot(2,1,1)
    plt.imshow(a_xi_arr,extent=[x[0],x[-1],t[-1],t[0]],vmin=-max_min,vmax=max_min,\
            aspect='auto', interpolation = 'nearest')
    plt.xlabel('raw data at depth at %d cm' % z[row_z])
    plt.colorbar()
    pylab.subplot(2,1,2)
    plt.imshow(((a_xi_R+a_xi_L).real),extent=[x[0],x[-1],t[-1],t[0]],vmin=-max_min,vmax=max_min,\
            aspect = 'auto', interpolation = 'nearest')
    plt.xlabel('reconstructed data (a_xi_R+a_xi_L.real)  at depth %d cm' %z[row_z])
    plt.colorbar()
    plt.figure(2)
    pylab.subplot(2,1,1)
    plt.imshow((a_xi_L.real),extent=[x[0],x[-1],t[-1],t[0]],vmin=-max_min,vmax=max_min,\
            aspect='auto', interpolation = 'nearest')
    plt.xlabel('left (a_xi_L.real) ')
    plt.colorbar()
    pylab.subplot(2,1,2)
    plt.imshow((a_xi_R.real),extent=[x[0],x[-1],t[-1],t[0]],vmin=-max_min,vmax=max_min,\
            aspect='auto', interpolation = 'nearest')
    plt.xlabel('right (a_xi_R.real)')
    plt.colorbar()
    
    plot_data(kx,omega,F,F_R,F_L,K,O)
    nc.close()
    return

def plot_data(kx,omega,F,F_R,F_L,K,O):
    #plt.figure(4)
    #plt.imshow(K,extent=[omega[0],omega[-1],kx[0],kx[-1]],\
    #        interpolation = "nearest", aspect = "auto")
    #plt.xlabel('KX')
    #plt.colorbar()
    
    #plt.figure(5)
    #plt.imshow(O,extent =[omega[0],omega[-1],kx[0],kx[-1]],interpolation="nearest", aspect="auto")
    #plt.xlabel('omega')
    #plt.colorbar()
    
    plt.figure(6)
    pylab.subplot(1,2,1)
    plt.imshow(abs(F_R), extent= [omega[0],omega[-1],kx[0],kx[-1]], interpolation= "nearest", aspect = "auto")
    plt.xlabel('abs FFT_R')
    plt.colorbar()
    plt.subplot(1,2,2)
    plt.imshow(abs(F_L), extent= [omega[0],omega[-1],kx[0],kx[-1]], interpolation= "nearest", aspect = "auto")
    plt.xlabel('abs FFT_L')
    plt.colorbar()
    
    
    plt.figure(7)
    plt.subplot(2,1,1)
    plt.imshow(abs(F_L+F_R),extent=[omega[0],omega[-1],kx[0],kx[-1]],interpolation= "nearest", aspect = "auto")
    plt.xlabel('abs(F_L+F_R)  reconstructed')
    plt.colorbar()
    pylab.subplot(2,1,2)
    plt.imshow(abs(F),extent=[omega[0],omega[-1],kx[0],kx[-1]],interpolation ="nearest",aspect = "auto")
    plt.xlabel('FFT of the original data')
    plt.colorbar()

    #plt.show()
    return
    

def plot_fft(kx,kz,omega,F):
    # get the path to the nc file
    # Open &  Load the nc file
    print " kx shape", kx.shape
    print " kz shape", kz.shape
    print " omega shape", omega.shape

    path = "/Volumes/HD4/deltaN2/%d" % deltaN2_id
    filename = path + "/deltaN2.nc"
    nc = netCDF4.Dataset(filename)
    deltaN2 = nc.variables['deltaN2_array']
  
    t = nc.variables['time']
    t = t[100:300]
    a = nc.variables['column']
    x = a[600:1000]
    b = nc.variables['row']
    z = b[300:800]
    print "t : " ,t[0],"to " , t[-1]
    print "x : " ,x[0],"to " , x[-1]
    print "z : " ,z[0],"to " , z[-1]

    #plot kx_, kz_, omega_
    plt.figure(2)
    plt.subplot(1,3,1)
    dx = x[1]-x[0]
    dz = z[1]-z[0]
    dt = t[1]-t[0]
    
    #plt.imshow(dz[500,150:800,500:600].reshape(650,500),extent=[x[0],x[-1],z[0],z[-1]])
    #plt.title('length and depth window')
    
    plt.imshow(abs(mkx), interpolation='nearest',
               extent=[t[0], t[-1],z[0],z[-1]],
               vmin = 0, vmax = np.pi/dx,
               aspect='auto')
    plt.xlabel('t')
    plt.ylabel('z')
    plt.title('kx')
    #plt.colorbar(ticks=[1,3,5,7])
    plt.colorbar()
    plt.subplot(1,3,2)
    plt.imshow(abs(mkz), interpolation='nearest',
               extent=[t[0], t[-1], x[0], x[-1]],
               vmin = 0, vmax = np.pi/dz ,
               aspect='auto')
    plt.xlabel('t')
    plt.ylabel('x')
    plt.title('kz')
    #plt.colorbar(ticks=[1,3,5,7,9])
    plt.colorbar()
    
    plt.subplot(1,3,3)
    plt.imshow(abs(momega).T, interpolation='nearest',
               extent=[x[0], x[-1], z[0], z[-1]],
              vmin = 0, vmax = np.pi/dt,
               aspect='auto')
    plt.xlabel('x')
    plt.ylabel('z')
    plt.title('omega')
    #plt.colorbar(ticks=[1,3,5,7,9])
    plt.colorbar()
    
    plt.savefig('/Volumes/HD2/users/prajvala/IGW_reflection/results/img1.jpeg')
    nc.close()
    plt.show()

def testing_HT():
    # Implementing the Hilbert transform with a simple cosine function
    
    # Defining the function f1,f2, and f = f1+f2
    xmin,xmax,dx = 0,200,1
    tmin,tmax,dt = 0,100,0.5
    x = np.mgrid[xmin:xmax:dx]
    t = np.mgrid[tmin:tmax:dt]
    print "x & t:" , x.shape,t.shape 
    
    #X,T = np.meshgrid(x,t)
    X,T = np.mgrid[xmin:xmax:dx,tmin:tmax:dt]
    nx,nt = len(x),len(t)
    A,B = 14.0, 26.0
    #kx = 0.20
    #W = 7
    kx = 0.5
    W= 1
    #W = 50 
    
    f1 = A * np.cos(W*T - kx*X)*1.0
    f2 = B * np.cos(W*T + kx*X)*1.0
    f = f1 + f2

    #plotting the 3 functions
    plt.figure(1)
    pylab.subplot(2,1,1)
    plt.imshow(f1,extent=[x[0],x[-1],t[0],t[-1]],vmin=-24.0,vmax=24.0)
    plt.xlabel('f1')
    plt.colorbar()
    pylab.subplot(2,1,2)
    plt.imshow(f2,extent=[x[0],x[-1],t[0],t[-1]],vmin=-24.0,vmax=24.0)
    plt.xlabel('f2')
    plt.colorbar()
    plt.figure(2)
    plt.imshow(f,extent=[x[0],x[-1],t[0],t[-1]])
    plt.xlabel('function f= f1+f2')
    plt.colorbar()
    
    # implementing HT

    #  STEP1: Calculate the FFT
    fft_f = np.fft.fft2(f)
    F = np.fft.fftshift(fft_f)
    
    print "x:",X.shape,"\nT: " ,T.shape," \n F: ",f.shape,"\nFFT of f: " ,fft_f.shape
    
    #calculating the horizontal wavenumber and the omega of the function
    wavenum = np.fft.fftfreq(nx, dx)
    wavenum = 2*np.pi*np.fft.fftshift(wavenum)
    omega = np.fft.fftfreq(nt, dt)
    omega = 2*np.pi*np.fft.fftshift(omega)
    print "wavenum: ", wavenum.shape, "\n omega: ", omega.shape
    OM,KX= np.meshgrid(omega,wavenum)
    print "KX: ", KX.shape, "\n OM: ", OM.shape
    
    # Call the function that filters out negative frequencies in fourier space
    # and multiplies the result by a constant 2.0 and separates out the +ve and
    # -ve wavenumbers

    rFFT,lFFT = filter_LR(KX,OM,F)
    
    print "RFFT:", rFFT.shape, "\nLFFT :", lFFT.shape      
    plt.figure(5)
    pylab.subplot(2,1,1)
    plt.imshow(rFFT.real,extent=[wavenum[0],wavenum[-1],omega[0],omega[-1]],interpolation='nearest',aspect='auto')
    plt.xlabel('right fft')
    plt.colorbar()
    pylab.subplot(2,1,2)
    plt.imshow(lFFT.real,extent=[wavenum[0],wavenum[-1],omega[0],omega[-1]],interpolation='nearest',aspect='auto')
    plt.xlabel('left fft')
    plt.colorbar()
    
    
    #inverse shift the 2 components and ifft-ing them to get the right and left
    # propagating waves
    F_Rinvs = np.fft.ifftshift(rFFT)
    deltaN2_R = np.fft.ifft2(F_Rinvs)
    F_Linvs = np.fft.ifftshift(lFFT)
    deltaN2_L = np.fft.ifft2(F_Linvs)
    print "deltaN2_R: " ,deltaN2_R.shape, "\n deltaN2_L: ", deltaN2_L.shape

    # plotting the results
    plt.figure(3)
    plt.imshow(F.real,extent=[wavenum[0],wavenum[-1],omega[0],omega[-1]],interpolation='nearest',aspect='auto')
    plt.xlabel('fft of f=f1+f1 ')
    plt.colorbar()
    plt.figure(4)
    pylab.subplot(2,1,1)
    plt.imshow(deltaN2_R.real,extent=[x[0],x[-1],t[0],t[-1]],vmin=-24.0,vmax=24.0,interpolation='nearest',aspect ='auto')
    plt.xlabel('right')
    plt.colorbar()
    pylab.subplot(2,1,2)
    plt.imshow(deltaN2_L.real,extent=[x[0],x[-1],t[0],t[-1]],vmin=-24.0,vmax =24.0,interpolation='nearest', aspect ='auto')
    plt.xlabel('left')
    plt.colorbar()

    plt.show()

    return




def test():

    
    """
    Test dominant frequency finding routine
    """

    # create a grid for x, z, t
    
    
    xmin, xmax, nx = 0, 10, 50
    zmin, zmax, nz = 0, 100, 100
    tmin, tmax, dt = 0, 100, 0.5
    x = np.mgrid[xmin:xmax:nx*1j]
    z = np.mgrid[zmin:zmax:nz*1j]
    t = np.mgrid[tmin:tmax:dt]
    print "x",x.shape, "z ", z.shape,"t ",t.shape
    X, Z, T = np.mgrid[xmin:xmax:nx*1j,
                       zmin:zmax:nz*1j,
                       tmin:tmax:dt]
    print "X",X.shape, "Z ", Z.shape,"T ",T.shape
    # ensure nx, nz, nt, dx, dz, dt are all defined
    nx, nz, nt = len(x), len(z), len(t)
    dx = x[1] - x[0]
    dz = z[1] - z[0]
    dt = t[1] - t[0]

    # change here to explore different functional forms
    kx0 = 2.0
    kz0 = 2.0
    omega0 = 2.0
    f = np.cos(kx0*X + kz0*Z - omega0*T)
    print "F:",f.shape
    # find the peak frequencies
    kx_, kz_, omega_ = estimate_dominant_frequency(f, x, z, t)

    # plot kx_, kz_, omega_
    # The titles should match colorbars if this is working correctly
    plt.figure(figsize=(182,5))

    plt.subplot(1,3,1)
    plt.imshow(abs(kx_).T, interpolation='nearest',
               extent=[zmin, zmax, tmin, tmax],
               vmin = 0, vmax = np.pi/dx,
               aspect='auto')
    plt.xlabel('z')
    plt.ylabel('t')
    plt.title('kx_ = %.2f' % kx0)
    plt.colorbar()

    plt.subplot(1,3,2)
    plt.imshow(abs(kz_).T, interpolation='nearest',
               extent=[xmin, xmax, tmin, tmax],
               vmin = 0, vmax = np.pi/dz,
               aspect='auto')
    plt.xlabel('x')
    plt.ylabel('t')
    plt.title('kz_ = %.2f' % kz0)
    plt.colorbar()

    plt.subplot(1,3,3)
    plt.imshow(abs(omega_).T, interpolation='nearest',
               extent=[xmin, xmax, zmin, zmax],
              vmin = 0, vmax = np.pi/dt,
               aspect='auto')
    plt.xlabel('x')
    plt.ylabel('z')
    plt.title('omega_ = %.2f' % omega0)
    plt.colorbar()

def UI():
    
    parser = argparse.ArgumentParser()
    parser.add_argument("a_xi_id",type=int,help="Enter the a_xi id of the \
            vertical displacement amplitude to FFT.")
    
    """parser.add_argument("t_start", type=int,help=" start: time step")
    parser.add_argument("t_end", type=int,help="stop: time step")
    parser.add_argument("r_start", type=int,help=" start: row pixel (window height)")
    parser.add_argument("r_end", type=int,help="stop: row pixel(0-963)")
    parser.add_argument("c_start", type=int,help="start: column pixel (window length)")
    parser.add_argument("c_end", type=int,help="Stop: column pixel (0-1291)")
    parser.add_argument("t_step", type=int,help=" steps to jump in time")
    parser.add_argument("r_step", type=int,help="steps to jump in row")
    parser.add_argument("c_step", type=int,help="steps to jump in column")
    """

    parser.add_argument("maxmin",type=float,help = "Enter the number to be\
            used as vmax and vmin in graphs and plots")
    parser.add_argument("plot_column",type=int,help = "Enter the column whose\
            timeseries you want in graphs and plots")
    args = parser.parse_args()
    #task_hilbert_func(args.a_xi_id,args.t_start,args.t_end,args.r_start,args.r_end,\
    #        args.c_start,args.c_end,args.t_step,args.r_step,args.c_step,args.maxmin) 
    task_hilbert_func(args.a_xi_id,args.maxmin,args.plot_column)

if __name__ == "__main__":
    #test()
    #testing_HT()
    UI()
