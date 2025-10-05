// Простой тест API клиента
import { pythonAPI } from './src/api/pythonApi.js'

async function testStationsAPI() {
  try {
    console.log('Тестируем API станций...')
    
    const response = await pythonAPI.getStations()
    console.log('Ответ API:', response)
    console.log('Тип ответа:', typeof response)
    console.log('Это массив?', Array.isArray(response))
    
    if (response && response.data) {
      console.log('Данные в поле data:', response.data)
      console.log('Количество станций:', response.data.length)
    }
    
  } catch (error) {
    console.error('Ошибка API:', error)
  }
}

testStationsAPI()
