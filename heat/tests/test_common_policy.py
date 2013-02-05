# Copyright 2012 OpenStack, LLC
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mox
import json
import unittest
from nose.plugins.attrib import attr

import os.path

import heat.api
from heat.common import context
from heat.common import policy
from heat.common import exception
from heat.openstack.common import cfg


@attr(tag=['unit', 'common-policy', 'Enforcer'])
@attr(speed='fast')
class TestPolicyEnforcer(unittest.TestCase):
    cfn_actions = ("ListStacks", "CreateStack", "DescribeStacks",
                   "DeleteStack", "UpdateStack", "DescribeStackEvents",
                   "ValidateTemplate", "GetTemplate",
                   "EstimateTemplateCost", "DescribeStackResource",
                   "DescribeStackResources")

    def setUp(self):
        self.path = os.path.dirname(os.path.realpath(__file__)) + "/policy/"
        self.m = mox.Mox()
        opts = [
            cfg.StrOpt('config_dir', default=self.path),
            cfg.StrOpt('config_file', default='foo'),
            cfg.StrOpt('project', default='heat'),
        ]
        cfg.CONF.register_opts(opts)
        print "setup complete"

    def tearDown(self):
        self.m.UnsetStubs()
        print "teardown complete"

    def test_policy_cfn_default(self):
        enforcer = policy.Enforcer(scope='cloudformation')

        ctx = context.RequestContext(roles=[])
        for action in self.cfn_actions:
            # Everything should be allowed
            enforcer.enforce(ctx, action, {})

    def test_policy_cfn_notallowed(self):
        pf = self.path + 'notallowed.json'
        self.m.StubOutWithMock(policy.Enforcer, '_find_policy_file')
        policy.Enforcer._find_policy_file().MultipleTimes().AndReturn(pf)
        self.m.ReplayAll()

        enforcer = policy.Enforcer(scope='cloudformation')

        ctx = context.RequestContext(roles=[])
        for action in self.cfn_actions:
            # Everything should raise the default exception.Forbidden
            self.assertRaises(exception.Forbidden, enforcer.enforce, ctx,
                              action, {})
        self.m.VerifyAll()

    def test_policy_cfn_deny_stack_user(self):
        pf = self.path + 'deny_stack_user.json'
        self.m.StubOutWithMock(policy.Enforcer, '_find_policy_file')
        policy.Enforcer._find_policy_file().MultipleTimes().AndReturn(pf)
        self.m.ReplayAll()

        enforcer = policy.Enforcer(scope='cloudformation')

        ctx = context.RequestContext(roles=['heat_stack_user'])
        for action in self.cfn_actions:
            # Everything apart from DescribeStackResource should be Forbidden
            if action == "DescribeStackResource":
                enforcer.enforce(ctx, action, {})
            else:
                self.assertRaises(exception.Forbidden, enforcer.enforce, ctx,
                                  action, {})
        self.m.VerifyAll()

    def test_policy_cfn_allow_non_stack_user(self):
        pf = self.path + 'deny_stack_user.json'
        self.m.StubOutWithMock(policy.Enforcer, '_find_policy_file')
        policy.Enforcer._find_policy_file().MultipleTimes().AndReturn(pf)
        self.m.ReplayAll()

        enforcer = policy.Enforcer(scope='cloudformation')

        ctx = context.RequestContext(roles=['not_a_stack_user'])
        for action in self.cfn_actions:
            # Everything should be allowed
            enforcer.enforce(ctx, action, {})
        self.m.VerifyAll()
