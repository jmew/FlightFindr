import axios from 'axios';

const testData = {
  startLocation: 'Seattle',
  endLocation: 'Seattle',
  intermediateStops: ['Auckland', 'sydney', 'bali'],
  startDate: '2025-11-12',
  endDate: '2025-12-06',
  maxLength: '14',
  constraints: '',
  flexible: true,
};

async function runTest() {
  try {
    const response = await axios.post(
      'http://localhost:3000/multi-city?sessionId=test-session',
      testData,
      { responseType: 'stream' }
    );

    const stream = response.data;

    stream.on('data', (chunk: Buffer) => {
      console.log(chunk.toString());
    });

    stream.on('end', () => {
      console.log('\n--- Test Finished ---');
    });

    stream.on('error', (err: Error) => {
      console.error('\n--- Test Error ---');
      console.error(err);
    });

  } catch (error) {
    if (axios.isAxiosError(error)) {
        console.error('Axios error:', error.message);
        if (error.response) {
            console.error('Status:', error.response.status);
            console.error('Data:', error.response.data);
        }
    } else {
        console.error('An unexpected error occurred:', error);
    }
  }
}

runTest();
