import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Triangle } from 'lucide-react';
import './Education.css';

const Education = () => {
  const [expandedItems, setExpandedItems] = useState({});

  const toggleItem = (catIdx, itemIdx) => {
    const key = `${catIdx}-${itemIdx}`;
    setExpandedItems(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const categories = [
    {
      title: 'Baby Development',
      items: [
        { label: 'First trimester', desc: 'Vital organs begin forming. Fatigue and nausea are common, and early appointments help establish care.', details: 'During weeks 1-12, the heart begins to beat, the brain and spinal cord form, and the limbs start to develop. If symptoms feel severe or worrying, contact your healthcare provider.' },
        { label: 'Second trimester', desc: 'Movement often begins. This is also when many fetal brain structures become easier to see on ultrasound.', details: 'Weeks 13-26 are often when anatomy scans happen. If you receive a scan report, ask your provider what was clearly visible, what needs follow-up, and when to return.' },
        { label: 'Third trimester', desc: 'Growth speeds up and your care team watches position, movement, and readiness for birth.', details: 'Weeks 27 until birth. You may feel more pressure and discomfort as the baby moves into birth position. Contact your provider urgently for severe pain, bleeding, fever, or reduced movement.' }
      ]
    },
    {
      title: 'Nutrition & Health',
      items: [
        { label: 'Folic acid', desc: 'An important nutrient for brain and spinal cord development.', details: 'A daily supplement of 400-800 mcg is often recommended to help prevent neural tube defects. Foods rich in folic acid include leafy greens, beans, and fortified cereals.' },
        { label: 'Iron and protein', desc: 'Supports increased blood volume and steady growth.', details: 'Iron helps prevent anemia, which is common in pregnancy. Protein supports your baby\'s cells. Lean meats, eggs, beans, and legumes are common sources.' },
        { label: 'Hydration', desc: 'Aim for 8-10 glasses of water daily.', details: 'Proper hydration helps form amniotic fluid, supports extra blood volume, and can help prevent UTIs and constipation.' }
      ]
    }
  ];

  return (
    <div className="education-view fade-in">
      <section className="edu-hero glass">
        <h2>Learning room</h2>
        <p>Short, steady explanations you can open when questions come up.</p>
      </section>

      <div className="edu-grid">
        {categories.map((cat, catIdx) => (
          <div key={catIdx} className="edu-card glass-card">
            <div className="card-header">
              <span className="card-icon">{cat.icon}</span>
              <h3>{cat.title}</h3>
            </div>
            <div className="card-body">
              {cat.items.map((item, itemIdx) => {
                const isExpanded = expandedItems[`${catIdx}-${itemIdx}`];
                return (
                  <div 
                    key={itemIdx} 
                    className={`edu-item ${isExpanded ? 'active' : ''}`} 
                    onClick={() => toggleItem(catIdx, itemIdx)}
                  >
                    <div className="edu-item-header">
                      <h4>{item.label}</h4>
                      {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                    </div>
                    <p className="edu-desc">{item.desc}</p>
                    {isExpanded && (
                      <div className="edu-details fade-in">
                        <div className="details-divider"></div>
                        <p>{item.details}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Education;
