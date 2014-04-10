"""
    SoftLayer.load_balancer
    ~~~~~~~~~~~~~~~~~~
    Load Balancer Manager/helpers

    :license: MIT, see LICENSE for more details.
"""
from SoftLayer.utils import IdentifierMixin, NestedDict, query_filter

class LoadBalancerManager(IdentifierMixin, object):

    """ Manages load balancers.

    :param SoftLayer.API.Client client: the API client instance

    """

    def __init__(self, client):
        self.client = client
        self.account = self.client['Account']
        self.prod_pkg = self.client['Product_Package']
        self.lb_svc = self.client['Network_Application_Delivery_Controller_'
                                  'LoadBalancer_VirtualIpAddress']

    def get_lb_pkgs(self):
        """ Retrieves the local load balancer packages.

        :returns: A dictionary containing the load balancer packages
        """

        lb_filter = '*Load Balancer*'
        _filter = NestedDict({})
        _filter['items']['description'] = query_filter(lb_filter)

        kwargs = NestedDict({})
        kwargs['id'] = 0  # look at package id 0
        kwargs['filter'] = _filter.to_dict()
        packages = self.prod_pkg.getItems(**kwargs)
        for package in packages:
            if package['description'].startsWith('Global'):
                packages.remove(package)
        return packages

    def get_ip_address(self, ip_address=None):
        """ Retrieves the IP address object given the ip address itself

        :returns: A dictionary containing the IP address properties
        """
        svc = self.client['Network_Subnet_IpAddress']
        return svc.getByIpAddress(ip_address)

    def get_hc_types(self):
        """ Retrieves the health check type values

        :returns: A dictionary containing the health check types
        """
        svc = self.client['Network_Application_Delivery_Controller_'
                          'LoadBalancer_Health_Check_Type']
        return svc.getAllObjects()

    def get_routing_methods(self):
        """ Retrieves the load balancer routing methods.

        :returns: A dictionary containing the load balancer routing methods
        """
        svc = self.client['Network_Application_Delivery_Controller_'
                          'LoadBalancer_Routing_Method']
        return svc.getAllObjects()

    def get_routing_types(self):
        """ Retrieves the load balancer routing types.

        :returns: A dictionary containing the load balancer routing types
        """
        svc = self.client['Network_Application_Delivery_Controller_'
                          'LoadBalancer_Routing_Type']
        return svc.getAllObjects()

    def get_location(self, datacenter):
        """ Returns the location of the specified datacenter

        :param string datacenter: The datacenter to create the loadbalancer in

        :returns: the location id of the given datacenter
        """
        _filter = NestedDict({})
        dcenters = self.client['Location'].getDataCenters()
        for dcenter in dcenters:
            if dcenter['name'] == datacenter:
                return dcenter['id']
        return 'FIRST_AVAILABLE'

    def cancel_lb(self, loadbal_id):
        """ Cancels the specified load balancer.

        :param int loadbal_id: Load Balancer ID to be cancelled.
        """
        lb_billing = self.lb_svc.getBillingItem(id=loadbal_id)
        billing_id = lb_billing['id']
        billing_item = self.client['Billing_Item']
        return billing_item.cancelService(id=billing_id)

    def add_local_lb(self, price_item_id, datacenter):
        """ Creates a local load balancer in the specified data center

        :param int price_item_id: The price item ID for the load balancer
        :param string datacenter: The datacenter to create the loadbalancer in

        :returns: A dictionary containing the product order
        """
        product_order = {
            'complexType': 'SoftLayer_Container_Product_Order_Network_'
                           'LoadBalancer',
            'quantity': 1,
            'packageId': 0,
            "location": self.get_location(datacenter),
            'prices': [{'id': price_item_id}]
        }
        return self.client['Product_Order'].placeOrder(product_order)

    def get_local_lbs(self):
        """ Returns a list of all local load balancers on the account.

        :returns: A list of all local load balancers on the current account.
        """
        mask = ('mask[loadBalancerHardware[datacenter],ipAddress]')
        return self.account.getAdcLoadBalancers(mask=mask)

    def get_local_lb(self, loadbal_id, **kwargs):
        """ Returns a specified local load balancer given the id.
        :param int loadbal_id: The id of the load balancer to retrieve

        :returns: A dictionary containing the details of the load balancer
        """
        # virtualServers.serviceGroups.services.ipAddress
        if 'mask' not in kwargs:
            kwargs['mask'] = ('mask[loadBalancerHardware[datacenter], '
                              'ipAddress, virtualServers[serviceGroups'
                              '[routingMethod,routingType,services'
                              '[healthChecks[type], groupReferences,'
                              ' ipAddress]]]]')

        return self.lb_svc.getObject(id=loadbal_id, **kwargs)

    def delete_service(self, loadbal_id, service_id):
        """ Deletes a service from the loadbal_id

        :param int loadbal_id: The id of the loadbal where the service resides
        :param int service_id: The id of the service to delete
        """
        svc = self.client['Network_Application_Delivery_Controller_'
                          'LoadBalancer_Service']

        return svc.deleteObject(id=service_id)

    def delete_service_group(self, loadbal_id, group_id):
        """ Deletes a service group from the loadbal_id

        :param int loadbal_id: The id of the loadbal where the service resides
        :param int group_id: The id of the service group to delete
        """
        svc = self.client['Network_Application_Delivery_Controller_'
                          'LoadBalancer_VirtualServer']

        return svc.deleteObject(id=group_id)

    def toggle_service_status(self, loadbal_id, service_id):
        """ Toggles the service status

        :param int loadbal_id: The id of the loadbal where the service resides
        :param int service_id: The id of the service to delete
        """
        svc = self.client['Network_Application_Delivery_Controller_'
                          'LoadBalancer_Service']
        return svc.toggleStatus(id=service_id)

    def edit_service(self, loadbal_id, service_id, ip_address_id=0, port=-1,
                     enabled=-1, hc_type=-1, weight=-1):
        """ Edits an existing service properties
        :param int loadbal_id: The id of the loadbal where the service resides
        :param int service_id: The id of the service to edit
        :param string ip_address: The ip address of the service
        :param int port: the port of the service
        :param int enabled: 1 to enable the service, 0 to disable it
        :param int hc_type: The health check type
        :param int weight: the weight to give to the service
        """
        _filter = NestedDict({})
        _filter['virtualServers']['serviceGroups']['services']['id'] = \
            query_filter(service_id)

        kwargs = NestedDict({})
        kwargs['filter'] = _filter.to_dict()
        kwargs['mask'] = ('mask[serviceGroups[services[groupReferences,'
                          'healthChecks]]]')

        virtual_servers = self.lb_svc.getVirtualServers(id=loadbal_id,
                                                        **kwargs)

        for service in virtual_servers[0]['serviceGroups'][0]['services']:
            if service['id'] == service_id:
                if enabled != -1:
                    service['enabled'] = enabled
                if port != -1:
                    service['port'] = port
                if weight != -1:
                    service['groupReferences'][0]['weight'] = weight
                if hc_type != -1:
                    service['healthChecks'][0]['healthCheckTypeId'] = hc_type
                if ip_address_id != 0:
                    service['ipAddressId'] = ip_address_id

        template = {'virtualServers': virtual_servers}

        load_balancer = self.lb_svc.editObject(template, id=loadbal_id)
        return load_balancer

    def add_service(self, loadbal_id, service_group_id, ip_address_id,
                    port=80, enabled=1, hc_type=21, weight=1):
        """ Adds a new service to the service group
        :param int loadbal_id: The id of the loadbal where the service resides
        :param int service_group_id: The group to add the service to
        :param int ip_address id: The ip address ID of the service
        :param int port: the port of the service
        :param int enabled: 1 to enable the service, 0 to disable it
        :param int hc_type: The health check type
        :param int weight: the weight to give to the service
        """
        kwargs = NestedDict({})
        kwargs['mask'] = ('mask[virtualServers[serviceGroups'
                          '[services[groupReferences]]]]')

        load_balancer = self.lb_svc.getObject(id=loadbal_id, **kwargs)
        virtual_servers = load_balancer['virtualServers']
        for virtual_server in virtual_servers:
            if virtual_server['id'] == service_group_id:
                service_template = {
                    'enabled': enabled,
                    'port': port,
                    'ipAddressId': ip_address_id,
                    'healthChecks': [
                        {
                            'healthCheckTypeId': hc_type
                        }
                    ],
                    'groupReferences': [
                        {
                            'weight': weight
                        }
                    ]
                    }
                virtual_server['serviceGroups'][0]['services']. \
                    append(service_template)

        return self.lb_svc.editObject(load_balancer, id=loadbal_id)

    def add_service_group(self, lb_id, allocation=100, port=80,
                          routing_type=2, routing_method=10):
        """ Adds a new service group to the load balancer
        :param int loadbal_id: The id of the loadbal where the service resides
        :param int allocation: the % of connections to allocate to the group
        :param int port: the port of the service group
        :param int routing_type: the routing type to set on the service group
        :param int routing_method: The routing method to set on the group
        """
        kwargs = NestedDict({})
        kwargs['mask'] = ('mask[virtualServers[serviceGroups'
                          '[services[groupReferences]]]]')
        load_balancer = self.lb_svc.getObject(id=lb_id, **kwargs)
        virtual_servers = load_balancer['virtualServers']
        service_template = {
            'port': port,
            'allocation': allocation,
            'serviceGroups': [
                {
                    'routingTypeId': routing_type,
                    'routingMethodId': routing_method
                }
            ]
        }

        virtual_servers.append(service_template)
        return self.lb_svc.editObject(load_balancer, id=lb_id)

    def edit_service_group(self, loadbal_id, group_id, allocation=-1, port=0,
                           routing_type=0, routing_method=0):
        """ Edit an existing service group
        :param int loadbal_id: The id of the loadbal where the service resides
        :param int group_id: The id of the service group
        :param int allocation: the % of connections to allocate to the group
        :param int port: the port of the service group
        :param int routing_type: the routing type to set on the service group
        :param int routing_method: The routing method to set on the group
        """
        kwargs = NestedDict({})
        kwargs['mask'] = 'mask[virtualServers[serviceGroups' \
                         '[services[groupReferences]]]]'

        load_balancer = self.lb_svc.getObject(id=loadbal_id, **kwargs)
        virtual_servers = load_balancer['virtualServers']
        for virtual_server in virtual_servers:
            if virtual_server['id'] == group_id:
                service_group = virtual_server['serviceGroups'][0]
                if allocation != -1:
                    virtual_server['allocation'] = allocation
                if port != 0:
                    virtual_server['port'] = port
                if routing_type != 0:
                    service_group['routingTypeId'] = routing_type
                if routing_method != 0:
                    service_group['routingMethodId'] = routing_method
        return self.lb_svc.editObject(load_balancer, id=loadbal_id)

    def reset_service_group(self, loadbal_id, group_id=None):
        """ Resets all the connections on the service group
        :param int loadbal_id: The id of the loadbal
        :param int group_id: The id of the service group to reset
        """
        _filter = NestedDict({})
        _filter['virtualServers']['id'] = query_filter(group_id)

        kwargs = NestedDict({})
        kwargs['filter'] = _filter.to_dict()
        kwargs['mask'] = 'mask[serviceGroups]'

        virtual_servers = self.lb_svc.getVirtualServers(id=loadbal_id,
                                                        **kwargs)
        actual_id = virtual_servers[0]['serviceGroups'][0]['id']

        svc = self.client['Network_Application_Delivery_Controller'
                          '_LoadBalancer_Service_Group']
        return svc.kickAllConnections(id=actual_id)
