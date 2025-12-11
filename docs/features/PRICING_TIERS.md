# 💰 Pricing Tiers & Business Model

**Date**: November 20, 2025

---

## 🎯 Pricing Structure (Recommended)

### 🆓 Free Plan (Personal Tracker)
**Target**: Individuals tracking personal finances

**Features**:
- ✅ 1 organization (personal)
- ✅ 1 user (yourself only)
- ✅ Unlimited transactions
- ✅ Unlimited budgets
- ✅ Unlimited projects
- ✅ Basic reports
- ✅ Invoice generation
- ✅ CSV upload/export
- ❌ No team members
- ❌ No role permissions
- ❌ No activity logging
- ❌ No approvals

**Price**: **FREE**

**Implementation**:
```python
plan='free'
max_users=1
```

---

### 💼 Professional Plan (Small Business)
**Target**: Small businesses, freelancers with small teams

**Features**:
- ✅ 1 organization
- ✅ Up to 5 team members
- ✅ Everything in Free, PLUS:
- ✅ Team collaboration
- ✅ Role-based permissions
- ✅ Activity logging & audit trail
- ✅ Advanced reports
- ✅ Priority email support
- ✅ Custom invoice templates
- ❌ Limited to 5 users
- ❌ No custom roles
- ❌ No approval workflows

**Price**: **$29/month** (or $290/year - save $58)

**Implementation**:
```python
plan='professional'
max_users=5
```

**Upgrade Prompt When**:
- User tries to invite 6th member
- User creates organization from UI

---

### 🏢 Enterprise Plan (Big Business)
**Target**: Medium to large businesses, accounting firms

**Features**:
- ✅ Unlimited organizations
- ✅ Unlimited team members
- ✅ Everything in Professional, PLUS:
- ✅ Custom role creation
- ✅ Approval workflows
- ✅ Advanced permissions (temporary access)
- ✅ API access
- ✅ SSO/SAML authentication
- ✅ Dedicated account manager
- ✅ Priority phone support
- ✅ Custom integrations
- ✅ White-label option

**Price**: **$99/month** (or custom pricing for 50+ users)

**Implementation**:
```python
plan='enterprise'
max_users=999  # essentially unlimited
```

---

## 🔧 How Pricing Is Enforced

### 1. Max Users Check (Already Implemented!)

**In Team Member Invitation** (`app_core/team_views.py`):

```python
# Check max users limit
if not org.can_add_member():
    return JsonResponse({
        'ok': False,
        'error': f'Organization has reached maximum members limit ({org.max_users}).'
    }, status=400)
```

**In Organization Model** (`app_core/team_models.py`):

```python
def can_add_member(self):
    """Check if organization can add more members"""
    current_count = self.members.filter(is_active=True).count()
    return current_count < self.max_users
```

### 2. Feature Gates (To Be Implemented)

**Custom Roles** (Enterprise only):
```python
@require_permission('can_manage_roles')
def create_custom_role(request):
    if request.organization.plan != 'enterprise':
        return error("Custom roles require Enterprise plan. Upgrade now!")
    # ... create role
```

**Approval Workflows** (Enterprise only):
```python
def create_approval_workflow(request):
    if request.organization.plan != 'enterprise':
        return error("Approval workflows require Enterprise plan.")
    # ... create workflow
```

**Multiple Organizations** (Enterprise only):
```python
def create_organization(request):
    user_orgs = Organization.objects.filter(owner=request.user).count()
    if user_orgs >= 1 and not has_enterprise_somewhere(request.user):
        return error("Multiple organizations require Enterprise plan.")
    # ... create org
```

### 3. Upgrade Prompts

**When user hits limit:**
```python
if not org.can_add_member():
    if org.plan == 'free':
        message = "Upgrade to Professional ($29/mo) to invite up to 5 team members!"
    elif org.plan == 'professional':
        message = "Upgrade to Enterprise for unlimited team members!"
    
    return show_upgrade_prompt(message)
```

---

## 💳 Billing Integration (Future)

### Recommended: Stripe

**Monthly Subscription:**
```python
# Stripe Products
STRIPE_PRODUCTS = {
    'professional': 'price_1234567890',  # $29/month
    'enterprise': 'price_0987654321',    # $99/month
}

# On upgrade
stripe.Subscription.create(
    customer=user.stripe_customer_id,
    items=[{'price': STRIPE_PRODUCTS['professional']}]
)
```

**Annual Discount:**
- Professional: $290/year (save $58 = 2 months free)
- Enterprise: $990/year (save $198 = 2 months free)

---

## 📊 Pricing Page Updates

### What to Show:

```
╔══════════════════════════════════════════════════════╗
║                     FREE                              ║
║                   $0/month                            ║
║                                                       ║
║  ✓ Personal finance tracking                         ║
║  ✓ Unlimited transactions                            ║
║  ✓ Basic reports                                     ║
║  ✓ 1 user only                                       ║
║                                                       ║
║            [Get Started Free]                        ║
╚══════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════╗
║                 PROFESSIONAL                          ║
║                  $29/month                            ║
║                                                       ║
║  ✓ Everything in Free                                ║
║  ✓ Up to 5 team members                              ║
║  ✓ Role-based permissions                            ║
║  ✓ Activity logging                                  ║
║  ✓ Priority support                                  ║
║                                                       ║
║            [Start 14-Day Trial]                      ║
╚══════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════╗
║                  ENTERPRISE                           ║
║                  $99/month                            ║
║                                                       ║
║  ✓ Everything in Professional                        ║
║  ✓ Unlimited team members                            ║
║  ✓ Custom roles & approvals                          ║
║  ✓ API access                                        ║
║  ✓ Dedicated support                                 ║
║                                                       ║
║            [Contact Sales]                           ║
╚══════════════════════════════════════════════════════╝
```

---

## 🎯 User Journey by Type

### Personal User (Free Forever):
1. Signs up → Auto Free plan
2. Uses for personal finance tracking
3. Never needs team features
4. Happy with free tier ✅

### Freelancer (Free → Professional):
1. Signs up → Free plan
2. Gets first client, wants to share invoice access
3. Tries to invite accountant → **BLOCKED**
4. Sees upgrade prompt: "Invite team members with Professional"
5. Upgrades to Professional $29/mo
6. Invites accountant (2/5 members)
7. Happy with Professional tier ✅

### Small Business (Professional):
1. Business owner signs up → Free
2. Immediately upgrades to Professional
3. Invites: CFO, 2 accountants, bookkeeper (5/5 members)
4. Uses all features
5. Happy with Professional tier ✅

### Growing Business (Professional → Enterprise):
1. Has 5 team members on Professional
2. Wants to add 6th member → **BLOCKED**
3. Sees: "Upgrade to Enterprise for unlimited members"
4. Also wants approval workflows (Enterprise only)
5. Upgrades to Enterprise $99/mo
6. Adds more team members
7. Sets up approval workflows
8. Happy with Enterprise tier ✅

### Enterprise Company (Enterprise):
1. Large company with 50+ employees
2. Needs custom integration
3. Contacts sales → Custom pricing
4. Gets Enterprise plan
5. Sets up SSO, custom roles, API access
6. Happy with custom Enterprise tier ✅

---

## 🚀 Implementation Roadmap

### Phase 1: Current (✅ DONE)
- ✅ Free tier with basic features
- ✅ Organization limits in database
- ✅ Max users enforcement
- ✅ Plan field in Organization model

### Phase 2: Basic Billing (Next)
- [ ] Pricing page with all tiers
- [ ] Stripe integration
- [ ] Subscription management
- [ ] Upgrade/downgrade flows
- [ ] Usage-based limits UI

### Phase 3: Advanced Features (Future)
- [ ] Custom roles (Enterprise)
- [ ] Approval workflows (Enterprise)
- [ ] API access (Enterprise)
- [ ] SSO authentication (Enterprise)
- [ ] White-label branding (Enterprise)

---

## 💡 Revenue Projections

### Conservative Estimate:

**Year 1:**
- 1,000 free users → $0
- 100 professional users @ $29/mo → $34,800/year
- 10 enterprise users @ $99/mo → $11,880/year
- **Total: $46,680/year**

**Year 2 (with growth):**
- 5,000 free users → $0
- 500 professional users @ $29/mo → $174,000/year
- 50 enterprise users @ $99/mo → $59,400/year
- **Total: $233,400/year**

**Year 3 (established):**
- 20,000 free users → $0
- 2,000 professional users @ $29/mo → $696,000/year
- 200 enterprise users @ $99/mo → $237,600/year
- **Total: $933,600/year**

### Key Metrics:
- **Free to Paid Conversion**: 10-15% (industry standard)
- **Professional to Enterprise**: 10-20%
- **Annual Plan Uptake**: 30-40%
- **Churn Rate Target**: <5% monthly

---

## 🔒 What's Already Built

✅ **Database structure** for plans
✅ **Member limits** enforced
✅ **Plan field** in Organization model
✅ **Team features** ready for Professional+
✅ **Permission system** ready for all tiers
✅ **Activity logging** for Professional+

**You're 80% there on the technical side!**

---

## 📝 Next Steps for Monetization

1. **Update pricing page** with real tiers
2. **Add Stripe integration**
3. **Create upgrade flows**
4. **Add usage indicators** (2/5 members used)
5. **Implement feature gates** for Enterprise features
6. **Add billing portal** for subscription management
7. **Create trial period** (14 days) for Professional

---

**The foundation is SOLID. Time to monetize! 💰**

