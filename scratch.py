import numpy as np
import matplotlib.pyplot as plt


def f(x, y):
    return np.sin(np.sqrt(x ** 2 + y ** 2))


if __name__ == "__main__":
    x2 = (20679845.340800002, 21522160.24288, 24129545.4528, 19123275.7408, 19514321.26688, 21930403.0528)
    y2 = (231152.38, 231152.38, 231152.38, 313072.38, 313072.38, 313072.38)
    z2 = (11520, 12672, 12800, 11520, 12672, 12800)
    ax = plt.axes(projection='3d')
    ax.scatter(x2, y2, z2)
    ax.set_xlabel('energy')
    ax.set_ylabel('area')
    ax.set_zlabel('cycle')
    ax.set_title('3D scatter')
    plt.show()