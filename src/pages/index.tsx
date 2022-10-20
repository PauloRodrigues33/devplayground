import type { NextPage } from 'next'
import Head from 'next/head'
import {Swiper, SwiperSlide} from 'swiper/react'
import 'swiper/css';

const Home: NextPage = () => {
  return (
    <div>
      <Head>
        <title>Developers Playground</title>
        <meta name="description" content="A open source project to developers test their ideas" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main>
        <Swiper>
          <SwiperSlide>Home</SwiperSlide>
          <SwiperSlide>Projects</SwiperSlide>
          <SwiperSlide>About</SwiperSlide>
        </Swiper>
      </main>
    </div>
  )
}

export default Home
