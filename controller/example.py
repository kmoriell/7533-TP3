from pox.core import core
import pox.openflow.discovery
import pox.openflow.spanning_tree
import pox.forwarding.l2_learning
from pox.lib.recoco import Timer
from pox.lib.util import dpid_to_str
from extensions.switch import SwitchController

log = core.getLogger()

class Controller:
  MAX_UDP_PACKETS = 10 # pkts/seg
  TIMER = 10 # segs
  paquetes_por_destino = dict()
  def __init__ (self):
    self.connections = set()
    self.switches = []

    # Esperando que los modulos openflow y openflow_discovery esten listos
    core.call_when_ready(self.startup, ('openflow', 'openflow_discovery'))

  def startup(self):
    """
    Esta funcion se encarga de inicializar el controller
    Agrega el controller como event handler para los eventos de
    openflow y openflow_discovery
    """
    core.openflow.addListeners(self)
    core.openflow_discovery.addListeners(self)
    log.info('Controller initialized')

  def _handle_ConnectionUp(self, event):
    """
    Esta funcion es llamada cada vez que un nuevo switch establece conexion
    Se encarga de crear un nuevo switch controller para manejar los eventos de cada switch
    """
    log.info("Switch %s has come up.", dpid_to_str(event.dpid))
    if (event.connection not in self.connections):
      self.connections.add(event.connection)
      sw = SwitchController(event.dpid, event.connection)
      self.switches.append(sw)
  
  def _handle_PacketIn (self, event):
    """
    Esta funcion es llamada cada que vez que se recibe un paquete.
    Aca es donde se va a implementar el firewall unicamente para paquetes UDP con un mismo
    destino que excedan un limite predefinido por unidad de tiempo.
    """
    log.info("Nuevo paquete recibido")
    frame = event.parsed
   
    if frame.type == frame.IP_TYPE:
      packet = frame.payload      
      if packet.protocol == packet.ICMP_PROTOCOL or packet.protocol == packet.UDP_PROTOCOL:
        if not packet.dstip in self.paquetes_por_destino.keys():
          self.paquetes_por_destino[packet.dstip] = 0
        self.paquetes_por_destino[packet.dstip] += 1

        if self.paquetes_por_destino[packet.dstip] >= self.MAX_UDP_PACKETS:
          log.info("Paquete bloqueado desde " + str(packet.dstip))
          event.halt = True         
        Timer(self.TIMER, self.reiniciar_bloqueos)
  
  def reiniciar_bloqueos(self):
    self.paquetes_por_destino.clear()

  def _handle_LinkEvent(self, event):
    """
    Esta funcion es llamada cada vez que openflow_discovery descubre un nuevo enlace
    """
    link = event.link
    log.info("Link has been discovered from %s,%s to %s,%s", dpid_to_str(link.dpid1), link.port1, dpid_to_str(link.dpid2), link.port2)

def launch():
  # Inicializando el modulo openflow_discovery
  pox.openflow.discovery.launch()

  # Registrando el Controller en pox.core para que sea ejecutado
  core.registerNew(Controller)

  """
  Corriendo Spanning Tree Protocol y el modulo l2_learning.
  No queremos correrlos para la resolucion del TP.
  Aqui lo hacemos a modo de ejemplo
  """
  pox.openflow.spanning_tree.launch()
  pox.forwarding.l2_learning.launch()
