const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const loadingIndicator = document.getElementById('loading-indicator');
const resultsContainer = document.getElementById('results-container');
const noDataContainer = document.getElementById('no-data-container');
const errorContainer = document.getElementById('error-container');
const errorMessage = document.getElementById('error-message');

let chartInstances = [];

// Topics in specific order
const ORDERED_TOPICS = [
    'placements', 'fees', 'faculty', 'hostel_food', 'campus_life', 'teaching', 'problems'
];

searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = searchInput.value.trim();
    if (!query) return;

    // UI state: loading
    loadingIndicator.classList.remove('hidden');
    resultsContainer.classList.add('hidden');
    noDataContainer.classList.add('hidden');
    errorContainer.classList.add('hidden');
    
    // Clear previous results
    resultsContainer.innerHTML = '';
    
    // Destroy previous charts
    chartInstances.forEach(chart => chart.destroy());
    chartInstances = [];

    try {
        const response = await fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: query })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        renderResults(data);
    } catch (error) {
        console.error("Error fetching data:", error);
        loadingIndicator.classList.add('hidden');
        errorContainer.classList.remove('hidden');
        errorMessage.textContent = "An error occurred while fetching data. Please ensure the backend is running.";
    }
});

function renderResults(data) {
    loadingIndicator.classList.add('hidden');

    if (!data.colleges_considered || data.colleges_considered.length === 0) {
        noDataContainer.classList.remove('hidden');
        return;
    }

    resultsContainer.classList.remove('hidden');

    // Handle comparative query with ranked_colleges instead of standard format
    if (data.ranked_colleges) {
        renderComparativeResults(data);
        return;
    }

    // Standard rendering for each college
    data.colleges_considered.forEach((college, index) => {
        const collegeData = data[college];
        if (!collegeData || !collegeData.sentiment_summary) return;

        const summary = collegeData.sentiment_summary;
        
        // Create section
        const section = document.createElement('div');
        section.className = 'college-section';
        
        const heading = document.createElement('h2');
        heading.textContent = college;
        section.appendChild(heading);

        // Prepare chart data
        const chartLabels = [];
        const chartScores = [];
        const chartColors = [];

        ORDERED_TOPICS.forEach(topic => {
            chartLabels.push(formatTopic(topic));
            const topicData = summary[topic];
            const score = topicData ? topicData.score : 0;
            chartScores.push(score);
            chartColors.push(getBarColor(score));
        });

        // Add Chart canvas container
        const chartDiv = document.createElement('div');
        chartDiv.className = 'chart-container';
        const canvas = document.createElement('canvas');
        canvas.id = `chart-${index}`;
        chartDiv.appendChild(canvas);
        section.appendChild(chartDiv);

        // Topic Cards
        const topicsContainer = document.createElement('div');
        topicsContainer.className = 'topics-container';

        ORDERED_TOPICS.forEach(topic => {
            const topicData = summary[topic];
            if (topicData) {
                const topicCard = createTopicCard(topic, topicData);
                topicsContainer.appendChild(topicCard);
            }
        });
        
        section.appendChild(topicsContainer);
        resultsContainer.appendChild(section);

        // Render chart
        const ctx = canvas.getContext('2d');
        const chartConfig = {
            type: 'bar',
            data: {
                labels: chartLabels,
                datasets: [{
                    label: 'Sentiment Score',
                    data: chartScores,
                    backgroundColor: chartColors,
                    borderWidth: 1,
                    borderColor: 'rgba(255, 255, 255, 0.1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: -1,
                        max: 1,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#8b8fa3'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#8b8fa3'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => `Score: ${context.raw.toFixed(2)}`
                        }
                    }
                }
            }
        };

        const newChart = new Chart(ctx, chartConfig);
        chartInstances.push(newChart);
    });
}

function renderComparativeResults(data) {
    const section = document.createElement('div');
    section.className = 'college-section';
    
    const heading = document.createElement('h2');
    heading.textContent = 'Comparison Results';
    section.appendChild(heading);
    
    data.ranked_colleges.forEach(rc => {
        const div = document.createElement('div');
        div.className = 'topic-card';
        div.style.borderLeftColor = getBarColor(rc.score);
        
        div.innerHTML = `
            <div class="topic-header">
                <div class="topic-title">${rc.college}</div>
                <div class="topic-stats">
                    <span class="score-badge" style="color: ${getBarColor(rc.score)}">Score: ${rc.score.toFixed(2)}</span>
                </div>
            </div>
            <p>Topic: ${formatTopic(rc.topic)}</p>
        `;
        section.appendChild(div);
    });
    
    resultsContainer.appendChild(section);
}

function createTopicCard(topicName, data) {
    const card = document.createElement('div');
    card.className = 'topic-card';
    
    // Set border color based on score
    const scoreColor = getBarColor(data.score);
    card.style.borderLeftColor = scoreColor;

    // Format consensus
    let consensusHtml = '';
    if (data.variance === null || data.variance === undefined) {
        consensusHtml = '<span class="badge consensus-na">N/A</span>';
    } else if (data.variance > 0.35) {
        consensusHtml = '<span class="badge consensus-divided">Divided</span>';
    } else {
        consensusHtml = '<span class="badge consensus-consensus">Consensus</span>';
    }

    // Header
    const header = document.createElement('div');
    header.className = 'topic-header';
    header.innerHTML = `
        <div class="topic-title">${formatTopic(topicName)}</div>
        <div class="topic-stats">
            <span class="score-badge" style="color: ${scoreColor}">${data.score.toFixed(2)}</span>
            <span class="badge confidence-badge">${data.confidence_label || 'Unknown'}</span>
            ${consensusHtml}
            <span class="sample-size">n=${data.sample_size || 0}</span>
        </div>
    `;
    card.appendChild(header);

    // Comments
    if (data.top_comments && data.top_comments.length > 0) {
        const excerptsContainer = document.createElement('div');
        
        const excerptsTitle = document.createElement('div');
        excerptsTitle.className = 'excerpts-title';
        excerptsTitle.textContent = 'Top Comments';
        excerptsContainer.appendChild(excerptsTitle);

        data.top_comments.forEach(comment => {
            const excerpt = document.createElement('div');
            excerpt.className = 'excerpt';
            
            const truncatedText = truncateWords(comment.text, 25);
            const link = \`https://www.reddit.com\${comment.permalink}\`;
            
            excerpt.innerHTML = `
                <div class="excerpt-text">"\${truncatedText}"</div>
                <div class="excerpt-meta">
                    <a href="\${link}" class="excerpt-link" target="_blank" rel="noopener noreferrer">View Source</a>
                    <span class="credibility">Credibility: \${comment.credibility_score ? comment.credibility_score.toFixed(2) : 'N/A'}</span>
                </div>
            `;
            excerptsContainer.appendChild(excerpt);
        });
        
        card.appendChild(excerptsContainer);
    }

    return card;
}

function getBarColor(score) {
    if (score > 0.2) {
        // Green
        return \`rgba(16, 185, 129, \${Math.min(0.4 + score * 0.6, 1)})\`; // Adjust opacity based on score
    } else if (score < -0.2) {
        // Red
        return \`rgba(239, 68, 68, \${Math.min(0.4 + Math.abs(score) * 0.6, 1)})\`;
    } else {
        // Grey
        return '#6b7280';
    }
}

function formatTopic(topic) {
    if (!topic) return '';
    return topic.split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}

function truncateWords(text, maxWords) {
    if (!text) return '';
    const words = text.split(/\\s+/);
    if (words.length <= maxWords) return text;
    return words.slice(0, maxWords).join(' ') + '...';
}
