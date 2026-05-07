# عقد إيجار

---

**الشقة:** {{ apartment }}

**بداية العقد:** {{ start_date }} | **نهاية العقد:** {{ end_date }}

**نوع الإيجار:** {{ rental_type }}

**مبلغ الإيجار اليومي/ الشهري:** {{ rental_amount }}

**التكلفة الإجمالية:** {{ total_cost }}

---

## العميل

**اسم العميل:** {{ client_name }}

**رقم إثبات الهوية:** {{ id_number }}

**رقم الهاتف:** {{ phone }}

**الجنسية:** {{ nationality }}

**نوعه:** {{ gender }}

---

## الشروط

{% for condition in conditions %}

- {{ condition }}
  {% endfor %}

---

**توقيع المستأجر:** {{ tenant_signature }} | **توقيع المسؤول:** {{ manager_signature }}
