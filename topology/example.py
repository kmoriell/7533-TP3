"""
Este archivo ejemplifica la creacion de una topologia de mininet
En este caso estamos creando una topologia muy simple con la siguiente forma

   host --- switch --- switch --- host
"""

import os

from mininet.topo import Topo


class Example(Topo):
    def __init__(self, half_ports = 2, **opts):
        Topo.__init__(self, **opts)

        niveles = int(os.environ['HEIGHT'])
        cant_de_sw = 0
        for i in range(1, niveles + 1):
            cant_de_sw += 2 ** (i - 1)
        print("Cantidad de switches " + str(cant_de_sw))
        switches = [None] * cant_de_sw

        # Primero creo los 3 hosts que se conectan a la raiz
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')

        sw_count = 1
        host_count = 4
        for nivel in range(1, niveles + 1):
            pos = 2 ** (nivel - 1) - 1
            for i in range(0, pos + 1):
                switches[pos + i] = self.addSwitch('sw' + str(sw_count))
                sw_count += 1

                # Agrego los links
        sw1 = switches[0]
        self.addLink(sw1, h1)
        self.addLink(sw1, h2)
        self.addLink(sw1, h3)

        for nivel in range(1, niveles + 1):
            pos = 2 ** (nivel - 1) - 1
            if nivel == niveles:
                # Estoy en el ultimo nivel, entonces tengo que agregarle a cada sw de este nivel
                # un host
                for i in range(0, pos + 1):
                    sw_actual = switches[pos + i]
                    host_it = self.addHost('h' + str(host_count))
                    host_count += 1
                    self.addLink(sw_actual, host_it)
                break
            for i in range(0, pos + 1):
                print("actual " + str(pos) + " + " + str(i))
                sw_actual = switches[pos + i]
                pos_sig_nivel = 2 ** nivel - 1
                for j in range(0, pos_sig_nivel + 1):
                    print("sig " + str(pos_sig_nivel) + " + " + str(j))
                    sw_it = switches[pos_sig_nivel + j]
                    self.addLink(sw_actual, sw_it)


topos = {'example': Example}
